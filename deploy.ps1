# Install Railway CLI if not already installed
if (!(Get-Command railway -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Railway CLI..."
    npm i -g @railway/cli
}

# Login to Railway
Write-Host "Logging in to Railway..."
railway login

# Initialize project
Write-Host "Initializing Railway project..."
railway init

# Set environment variables
Write-Host "Setting environment variables..."
railway variables set API_ID=$env:API_ID
railway variables set API_HASH=$env:API_HASH
railway variables set BOT_TOKEN=$env:BOT_TOKEN

# Deploy the bot
Write-Host "Deploying bot to Railway..."
railway up

Write-Host "Deployment complete! Check your Railway dashboard for status." 