#!/bin/bash

# Deploy script for PhD_Road website
# Usage: ./deploy.sh "commit message"

COMMIT_MSG="${1:-Update website}"

cd website
echo "🔨 Building with Quarto..."
quarto render || exit 1

echo "📁 Copying to root docs folder..."
cp -r docs ../docs || exit 1

cd ..
echo "📤 Pushing to GitHub..."
git add docs/
git commit -m "$COMMIT_MSG"
git push

echo "✅ Deployed! Visit: https://aivanleon.github.io/PhD_Road"
