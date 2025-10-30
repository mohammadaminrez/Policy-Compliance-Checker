#!/bin/sh

# Check if running on Railway (Railway sets RAILWAY_ENVIRONMENT)
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    echo "Running on Railway - using railway nginx config"
    cp /etc/nginx/nginx.railway.conf /etc/nginx/conf.d/default.conf
else
    echo "Running locally - using local nginx config"
    cp /etc/nginx/nginx.local.conf /etc/nginx/conf.d/default.conf
fi

# Start nginx
nginx -g "daemon off;"
