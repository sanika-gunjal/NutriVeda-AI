# Deploy NutriVeda AI (Render.com, free)

1. Push this folder to a GitHub repo.
2. render.com -> New -> Web Service -> connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Environment variables: SECRET_KEY (long random text), ADMIN_USERNAME, ADMIN_PASSWORD
   (optional: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)

Note: free hosting resets the SQLite database on redeploy/restart. For permanent
user data use a Render persistent disk or an external database.
