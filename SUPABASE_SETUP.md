# Setting Up Supabase for ELD Log

This guide will walk you through setting up a Supabase PostgreSQL database for your ELD Log application.

## 1. Sign Up for Supabase

1. Go to [Supabase](https://supabase.com/) and sign up for a free account.
2. Click on "New Project" to create a new project.
3. Choose a name for your project (e.g., "eld-log").
4. Set a secure database password (save it for later use).
5. Choose the region closest to your users.
6. Click "Create New Project".

## 2. Get Database Connection Information

Once your project is created:

1. Go to the "Settings" section in the left sidebar.
2. Click on "Database".
3. Scroll down to find your connection string under "Connection String".
4. There will be a URI that looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.example.supabase.co:5432/postgres
   ```
5. Copy this connection string.

## 3. Configure Render Environment Variables

1. In your Render dashboard, go to your "eld-log-api" web service.
2. Click on "Environment" in the left sidebar.
3. Find the "DATABASE_URL" environment variable.
4. Paste your Supabase connection string as the value.
5. Click "Save Changes".

## 4. Create Database Tables

There are two approaches to creating your database tables:

### Option 1: Manual Database Migration (Recommended for First Deployment)

1. Locally, update your `.env` file with the Supabase connection string:
   ```
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.example.supabase.co:5432/postgres
   ```
2. Run the migrations locally to create the tables:
   ```
   python manage.py migrate
   ```

### Option 2: Let Render Handle Migrations

This is already configured in your `build.sh` script, but it relies on having the correct DATABASE_URL environment variable set in Render before the first deployment.

## 5. Verify Database Connection

After deploying to Render:

1. Check your Render logs to confirm the database connection is successful.
2. In Supabase, go to the "Table Editor" section to verify your tables were created.

## Database Credentials Security

- Never commit your database credentials to your repository.
- Always use environment variables for sensitive information.
- Consider using Render's environment variable encryption for added security. 