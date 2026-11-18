#!/usr/bin/env bash
# Compare image sizes before/after Alpine migration

echo "📊 Image Size Comparison"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

BACKEND_OLD="python:3.11-slim-bookworm"
BACKEND_NEW="python:3.11-alpine"

echo "Base Image Sizes:"
echo "  Debian (slim-bookworm): ~200 MB"
echo "  Alpine (3.11-alpine):   ~80 MB"
echo "  Reduction:              ~60% smaller base"
echo ""

echo "Expected Final Image Sizes (with dependencies):"
echo "  Backend (old):  ~650-750 MB"
echo "  Backend (new):  ~350-450 MB (Alpine)"
echo "  Reduction:      ~40-45%"
echo ""

echo "Frontend (unchanged):"
echo "  ~150-200 MB"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To check actual sizes after build:"
echo "  docker images | grep janus"
echo "  docker inspect <image-id> | grep Size"
echo "  docker history <image-name> --no-trunc"
