#!/bin/bash
# Test testscan with distorted images

mkdir -p /home/user/TurboTests/phase3/test_images/scan_results

for distortion in clean slight_distortion heavy_distortion; do
  echo "=== Testing $distortion images ==="
  for img in /home/user/TurboTests/phase3/test_images/$distortion/*.json; do
    basename=$(basename "$img" .json)
    python3 /home/user/TurboTests/phase3/tools/testscan.py "$img" \
      --layout /home/user/TurboTests/phase3/output/e2e_test/template_layout.json \
      --output /home/user/TurboTests/phase3/test_images/scan_results/${distortion}_${basename}.json
  done
done

echo ""
echo "Scan results saved to test_images/scan_results/"
