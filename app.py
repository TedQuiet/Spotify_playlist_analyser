import os
from typing import List, Dict, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

SCOPE = "playlist-read-private playlist-read-collaborative"


def get_spotify_client() -> Optional[Spotify]:
    if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
        st.error(
            "Spotify credentials are missing. "
            "Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET and "
            "SPOTIFY_REDIRECT_URI in your .env file."
        )
        return None

    try:
        auth_manager = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            cache_path=".spotify_cache",
            show_dialog=False,
        )
        return Spotify(auth_manager=auth_manager)
    except Exception as e:
        st.error(f"Could not authenticate with Spotify: {e}")
        return None


def fetch_playlists(sp: Spotify) -> List[Dict]:
    playlists: List[Dict] = []
    results = sp.current_user_playlists(limit=50)
    for item in results.get("items", []):
        playlists.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "tracks_total": item.get("tracks", {}).get("total", 0),
            }
        )
    return playlists


def fetch_playlist_tracks(sp: Spotify, playlist_id: str) -> List[Dict]:
    tracks: List[Dict] = []
    results = sp.playlist_tracks(playlist_id, limit=100)

    while results:
        for item in results.get("items", []):
            track = item.get("track")
            if not track:
                continue

            artists = track.get("artists", []) or []
            artist_names = [a.get("name") for a in artists if a.get("name")]
            artist_ids = [a.get("id") for a in artists if a.get("id")]

            tracks.append(
                {
                    "id": track.get("id"),
                    "name": track.get("name"),
                    "artist": ", ".join(artist_names),
                    "artist_ids": artist_ids,
                    "album": track.get("album", {}).get("name"),
                    "duration_ms": track.get("duration_ms"),
                    "popularity": track.get("popularity"),
                }
            )

        if results.get("next"):
            results = sp.next(results)
        else:
            break

    return tracks


def add_genres_if_available(sp: Spotify, tracks: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(tracks)

    if "duration_ms" in df.columns:
        df["duration_min"] = (df["duration_ms"] / 60000).round(2)
    else:
        df["duration_min"] = None

    if "artist_ids" not in df.columns or df["artist_ids"].isna().all():
        df["genre"] = None
        return df

    artist_id_lists = df["artist_ids"].dropna().tolist()
    all_artist_ids = {aid for sub in artist_id_lists for aid in sub if aid}

    if not all_artist_ids:
        df["genre"] = None
        return df

    artist_ids_list = list(all_artist_ids)
    genres_map: Dict[str, List[str]] = {}
    batch_size = 50

    for start in range(0, len(artist_ids_list), batch_size):
        batch = artist_ids_list[start : start + batch_size]
        try:
            response = sp.artists(batch)
            artists = response.get("artists", [])
        except SpotifyException as e:
            st.warning(
                f"Spotify refused artist genre request for a batch of artists "
                f"(HTTP {e.http_status}). Skipping those artists."
            )
            continue

        for artist in artists:
            if not artist:
                continue
            aid = artist.get("id")
            if not aid:
                continue
            genres_map[aid] = artist.get("genres", []) or []

    def join_genres(artist_ids_row: List[str]) -> Optional[str]:
        if not isinstance(artist_ids_row, list) or not artist_ids_row:
            return None
        collected: List[str] = []
        for aid in artist_ids_row:
            genres = genres_map.get(aid, [])
            collected.extend(genres)
        if not collected:
            return None

        unique_genres = sorted(set(collected))
        return ", ".join(unique_genres)

    df["genre"] = df["artist_ids"].apply(join_genres)

    if "artist_ids" in df.columns:
        df = df.drop(columns=["artist_ids"])

    return df


def main() -> None:
    st.set_page_config(page_title="Spotify Playlist Analyzer", page_icon="🎧")

    st.title("Spotify Playlist Analyzer")
    st.write("Log in with your Spotify account and explore your playlists.")

    sp_user = get_spotify_client()
    if sp_user is None:
        st.stop()

    try:
        user = sp_user.current_user()
        display_name = user.get("display_name", "Unknown user")
        st.success(f"Logged in as {display_name}")
    except Exception as e:
        st.error(f"Could not fetch user profile: {e}")
        st.stop()

    playlists = fetch_playlists(sp_user)
    if not playlists:
        st.warning("No playlists found on this account.")
        st.stop()

    labels = [f"{p['name']} ({p['tracks_total']} tracks)" for p in playlists]
    choice = st.selectbox("Choose a playlist", labels)

    selected = playlists[labels.index(choice)]
    playlist_id = selected["id"]

    st.write(f"Selected playlist: **{selected['name']}**")

    with st.spinner("Fetching tracks and analysis..."):
        tracks = fetch_playlist_tracks(sp_user, playlist_id)
        if not tracks:
            st.warning("This playlist has no tracks")
            st.stop()

        df = add_genres_if_available(sp_user, tracks)

    st.subheader("Playlist summary")

    total_tracks = len(df)
    total_minutes = df["duration_min"].sum()
    avg_popularity = df["popularity"].dropna().mean()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tracks", int(total_tracks))
    with col2:
        st.metric(
            "Total length (hours)",
            f"{(total_minutes / 60):.2f}" if pd.notna(total_minutes) else "N/A",
        )
    with col3:
        st.metric(
            "Average popularity",
            f"{avg_popularity:.1f}" if pd.notna(avg_popularity) else "N/A",
        )

    st.subheader("Track details")
    st.dataframe(
        df[
            [
                "name",
                "artist",
                "genre",
                "album",
                "duration_min",
                "popularity",
            ]
        ]
    )

    st.subheader("Popularity distribution")
    st.bar_chart(df.set_index("name")["popularity"])

    st.subheader("Top artists in this playlist")
    top_artists = (
        df["artist"].str.split(", ", expand=True).stack().value_counts().head(10)
    )
    st.bar_chart(top_artists)

    st.subheader("Top genres in this playlist")
    if "genre" in df.columns and df["genre"].notna().any():
        top_genres = (
            df["genre"]
            .dropna()
            .str.split(", ", expand=True)
            .stack()
            .value_counts()
            .head(10)
        )
        st.bar_chart(top_genres)
    else:
        st.info("No genre information available for this playlist")

if __name__ == "__main__":
    main()
