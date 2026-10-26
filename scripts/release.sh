#!/usr/bin/env bash
# Release HEAD: build and push the image, run migrations, then deploy the service and the ingest job.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Commit or stash your changes first: the image is tagged with HEAD." >&2
  exit 1
fi

project=$(gcloud config get-value project)
commit=$(git rev-parse --short HEAD)
image="asia-northeast1-docker.pkg.dev/$project/kansei/kansei:$commit"

docker build --platform linux/amd64 -t "$image" .
docker push "$image"
gcloud run jobs deploy migrate --image="$image" --wait
gcloud run deploy kansei --image="$image"
gcloud run jobs deploy ingest --image="$image"

deployed=$(gcloud run jobs describe ingest --format='value(spec.template.spec.template.spec.containers[0].image)')
if [[ "$deployed" != "$image" ]]; then
  echo "ingest runs $deployed, expected $image" >&2
  exit 1
fi
echo "Released $commit"