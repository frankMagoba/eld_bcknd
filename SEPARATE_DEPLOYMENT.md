# Separate Deployment Guide for ELD Log

This guide provides detailed instructions for deploying the backend and frontend components separately on Render.

## Backend Deployment (Django API)

### 1. Prepare for Deployment

1. Make sure you have created a Supabase account and set up a database as outlined in [SUPABASE_SETUP.md](SUPABASE_SETUP.md).
2. Ensure your `build.sh` file is executable (has correct permissions).
3. Verify that all required Python packages are listed in `requirements.txt`.

### 2. Deploy to Render

1. Log in to your Render account.
2. Click on "New" and select "Web Service".
3. Connect to your GitHub repository.
4. Configure the service with the following settings:
   - **Name**: `eld-log-api` (or your preferred name)
   - **Root Directory**: `eld_log` (make sure this points to where your Django project is located)
   - **Environment**: `Python`
   - **Region**: Choose the region closest to your users
   - **Branch**: `main` (or your default branch)
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn eld_log.wsgi:application`
   - **Plan**: Free (or select a paid plan if needed)

5. Add the following environment variables under the "Environment" section:
   - `DATABASE_URL`: Your Supabase connection string
   - `SECRET_KEY`: A strong random string for Django's secret key
   - `DEBUG`: `false`
   - `PYTHON_VERSION`: `3.11.3` (or your preferred version)
   - `DJANGO_SETTINGS_MODULE`: `eld_log.settings`

6. Click "Create Web Service".

### 3. Verify Backend Deployment

1. Wait for the deployment to complete (this may take a few minutes).
2. Once deployed, visit your backend URL to verify it's working. You should see the Django or DRF interface.
3. Test an API endpoint like `https://your-backend-url.onrender.com/api/trips/` to confirm API functionality.

## Frontend Deployment (React App)

### 1. Update API URL

Before deploying, make sure your frontend is configured to use the correct backend API URL:

1. Create or update `.env.production` in your frontend directory with:
   ```
   VITE_API_URL=https://your-backend-url.onrender.com/api
   ```

2. Commit this change to your repository.

### 2. Deploy to Render

1. In your Render dashboard, click "New" and select "Web Service" again.
2. Connect to the same GitHub repository.
3. Configure the service with these settings:
   - **Name**: `eld-log-frontend` (or your preferred name)
   - **Root Directory**: `eld-log-frontend` (where your React app is located)
   - **Environment**: `Node`
   - **Region**: Choose the same region as your backend for best performance
   - **Branch**: `main` (or your default branch)
   - **Build Command**: `npm ci && npm run build`
   - **Start Command**: `npm run preview`
   - **Plan**: Free (or select a paid plan if needed)

4. Add these environment variables:
   - `VITE_API_URL`: Your backend API URL (e.g., `https://eld-log-api.onrender.com/api`)
   - `NODE_ENV`: `production`
   - `PORT`: `8080`

5. Click "Create Web Service".

### 3. Verify Frontend Deployment

1. Wait for the deployment to complete.
2. Visit your frontend URL and test the application functionality.
3. Ensure the frontend can successfully communicate with the backend API.

## Troubleshooting

### Backend Issues

- **Migrations not applied**: Check the Render logs. You may need to run migrations manually.
- **Database connection errors**: Verify your Supabase connection string is correct.
- **500 errors**: Check the Render logs for Python exceptions.

### Frontend Issues

- **API connection failures**: Ensure the `VITE_API_URL` is correct and the backend is accessible.
- **Blank page**: Check for JavaScript errors in the browser console.
- **Missing styles**: Confirm that the build process completed successfully.

## Maintenance

- **Updating the application**: Push changes to your GitHub repository. Render will automatically deploy the updates.
- **Monitoring**: Use Render's dashboard to monitor resource usage, logs, and performance.
- **Scaling**: If needed, upgrade your Render plan for more resources. 