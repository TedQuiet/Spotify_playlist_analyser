This is a Streamlit web application that connects to your Spotify account and provides interactive analytics for any playlist you choose.
It displays track details, calculates playlist statistics, retrieves genre information via the Spotify API, and generates visual insights such as top artists, genres, and popularity distribution.

Features:

Spotify Login
Secure OAuth login using your personal Spotify account
Accesses your playlists (private or collaborative)
Playlist Browser
Displays all playlists on your account
Shows track count for each playlist
Lets you select a playlist for analysis

Playlist Insights

Number of tracks
Total listening time (in hours)
Average track popularity
Top artists (bar chart)
Top genres (bar chart)
Popularity distribution chart
Track-Level Details

Each track in the playlist includes:

Name
Artists
Genre (derived from artist genres)
Album
Duration (minutes)
Popularity score

Installation:

1. Clone the repository
git clone https://github.com/YOUR_USERNAME/Spotify_playlist_analyzer.git
cd Spotify_playlist_analyzer

2. Create a virtual environment
Windows:

python -m venv venv
venv\Scripts\activate

macOS / Linux:

python3 -m venv venv
source venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. Configure Spotify API

i. Go to:

https://developer.spotify.com/dashboard

ii. Create a new app

iii. Add Redirect URI:
your_spotify_redirect_URI

iv. Create a .env file in your project folder:
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://your_spotify_redirect_URI

5. Run the app
streamlit run app.py
