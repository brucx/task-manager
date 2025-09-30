#!/bin/bash
# Start GPU workers on GPU server

set -e

echo "🎮 Starting GPU workers..."

# Check NVIDIA Docker runtime
if ! docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi > /dev/null 2>&1; then
    echo "❌ NVIDIA Docker runtime not available."
    echo "Please install nvidia-container-toolkit:"
    echo "  https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
    exit 1
fi

# Check GPU availability
GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
echo "📊 Found $GPU_COUNT GPUs"

if [ "$GPU_COUNT" -ne 8 ]; then
    echo "⚠️  Warning: Expected 8 GPUs, found $GPU_COUNT"
fi

# Create models directory
mkdir -p ./weights
echo "📁 Models directory: ./weights"
echo "   Place model files here:"
echo "   - general_model.pth"
echo "   - portrait_model.pth"
echo "   - landscape_model.pth"

# Start GPU workers
echo "🚀 Starting GPU worker containers..."
docker-compose -f docker-compose.gpu.yml up -d

# Wait for startup
sleep 5

# Check status
echo "📋 GPU worker status:"
docker-compose -f docker-compose.gpu.yml ps

echo ""
echo "✅ GPU workers started successfully!"
echo ""
echo "🔍 Monitor GPU utilization:"
echo "  watch -n 1 nvidia-smi"
echo ""