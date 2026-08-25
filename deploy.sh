#!/bin/bash

# Deploy script for PhD_Road website
# Usage: ./deploy.sh "commit message"

COMMIT_MSG="${1:-Update website}"

cd website
echo "🔨 Building with Quarto..."
quarto render || exit 1

echo "📁 Copying to root docs folder..."
rsync -a --delete _output/ ../docs/ || exit 1
touch ../docs/.nojekyll  # rsync --delete wipes it since Quarto doesn't emit it into _output

cd ..
echo "📤 Pushing to GitHub..."
git add docs/
git commit -m "$COMMIT_MSG"
git push

echo "✅ Deployed! Visit: https://aivanleon.github.io/PhD_Road"
