#!/usr/bin/env bash
# Setup Janus Environment Variables for PC1 and PC2

set -e

echo "🔧 Janus Environment Setup"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if env files exist
if [ ! -f .env.pc1.example ] || [ ! -f .env.pc2.example ]; then
    echo "❌ Missing .env.*.example files"
    exit 1
fi

echo "📋 Creating .env.pc1 (API, Frontend, Postgres, Redis, RabbitMQ)"
echo "───────────────────────────────────────────────────────────────"

if [ -f .env.pc1 ]; then
    read -p "⚠️  .env.pc1 already exists. Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping .env.pc1"
    else
        cp .env.pc1.example .env.pc1
        echo "✅ .env.pc1 reset from template"
    fi
else
    cp .env.pc1.example .env.pc1
    echo "✅ Created .env.pc1"
fi

echo ""
echo "📋 Creating .env.pc2 (Neo4j, Qdrant, Ollama)"
echo "───────────────────────────────────────────────────────────────"

if [ -f .env.pc2 ]; then
    read -p "⚠️  .env.pc2 already exists. Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping .env.pc2"
    else
        cp .env.pc2.example .env.pc2
        echo "✅ .env.pc2 reset from template"
    fi
else
    cp .env.pc2.example .env.pc2
    echo "✅ Created .env.pc2"
fi

echo ""
echo "⚙️  Environment Configuration"
echo "───────────────────────────────────────────────────────────────"
echo ""

echo "PC1 Required Variables (set in .env.pc1):"
grep -E "^.*:?" .env.pc1.example | grep "?" | head -10 || echo "  Check .env.pc1.example for details"
echo ""

echo "PC2 Required Variables (set in .env.pc2):"
grep -E "^.*:?" .env.pc2.example | grep "?" | head -10 || echo "  Check .env.pc2.example for details"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "✅ Setup Complete!"
echo ""
echo "Next Steps:"
echo "  1. Edit .env.pc1 with your configuration"
echo "  2. Edit .env.pc2 with your configuration"
echo "  3. Set Tailscale IPs for PC1↔PC2 communication"
echo ""
echo "To start services:"
echo "  PC1: docker compose -f docker-compose.pc1.yml up -d"
echo "  PC2: docker compose -f docker-compose.pc2.yml up -d"
echo ""
echo "To monitor logs:"
echo "  PC1: docker compose -f docker-compose.pc1.yml logs -f"
echo "  PC2: docker compose -f docker-compose.pc2.yml logs -f"
