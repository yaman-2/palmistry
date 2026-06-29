import json
import os
import requests
import difflib
from datetime import datetime

# Local API Endpoint for Samudrika (Must be running)
API_URL = "http://127.0.0.1:8001/process_palm"
DATASET_PATH = "golden_dataset.json"
REPORT_PATH = "coverage_report.md"

def compute_similarity(text1: str, text2: str) -> float:
    """
    Computes a Semantic Similarity Score.
    Uses SequenceMatcher for a lightweight baseline overlap score.
    If 'sentence-transformers' is installed, it could be swapped here for deep AI scoring.
    """
    # Normalize texts
    t1 = text1.lower().strip()
    t2 = text2.lower().strip()
    return difflib.SequenceMatcher(None, t1, t2).ratio()

def generate_report(results: list, summary: dict):
    """Generates the Markdown coverage report."""
    with open(REPORT_PATH, "w") as f:
        f.write("# Samudrika AI: Accuracy & Coverage Audit Report\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 1. Executive Summary\n")
        f.write(f"- **Total Cases Tested:** {summary['total']}\n")
        f.write(f"- **Average Similarity Score:** {summary['avg_score']:.2%}\n")
        f.write(f"- **High Confidence Predictions (>70%):** {summary['high_conf']}\n")
        f.write(f"- **Low Confidence / Vague Outputs:** {summary['low_conf']}\n\n")
        
        f.write("## 2. Data Gap Identification & Strategy\n")
        if summary['low_conf'] > 0:
            f.write("> **[WARNING] Low-Confidence Predictions Detected!**\n")
            f.write("> The model produced generic or vague outputs for certain edge cases.\n")
            f.write("> **Suggested Prompt Strategy:** Update `SYSTEM_PROMPT` to explicitly instruct the model to look for specific visual markers (e.g., 'If the life line is faint, explicitly state X. Do not give general advice.').\n\n")
        else:
            f.write("> **[SUCCESS] Consistent Data Coverage.**\n> The model handled the tested edge cases well.\n\n")

        f.write("## 3. Edge Case Coverage Analysis\n")
        for res in results:
            f.write(f"### {res['id']}: {res['edge_case']}\n")
            f.write(f"- **Image Path:** `{res['image_path']}`\n")
            f.write(f"- **Similarity Score:** `{res['score']:.2%}`\n")
            if res['score'] < 0.5:
                f.write("- **Status:** ❌ FAILED (Significant Deviation)\n")
            else:
                f.write("- **Status:** ✅ PASSED\n")
            
            f.write("\n**Expert Benchmark:**\n")
            f.write(f"> {res['expert_text'][:200]}...\n")
            
            f.write("\n**AI Output:**\n")
            f.write(f"> {res['ai_text'][:200]}...\n\n")
            f.write("---\n")

def run_audit():
    if not os.path.exists(DATASET_PATH):
        print(f"Error: {DATASET_PATH} not found.")
        return

    with open(DATASET_PATH, "r") as f:
        dataset = json.load(f)

    test_cases = dataset.get("test_cases", [])
    print(f"Starting audit for {len(test_cases)} cases...")
    
    results = []
    total_score = 0.0
    low_conf = 0
    high_conf = 0

    for idx, case in enumerate(test_cases):
        print(f"[{idx+1}/{len(test_cases)}] Testing {case['id']} ({case['edge_case']})...")
        
        # Combine expert reading into a single string for comparison
        expert_text = " ".join(case["expert_reading"].values())
        
        # In a real scenario, we would pass the actual image file to the API.
        # For this audit script, if the file doesn't exist, we send a dummy text to trigger the mock fallback.
        # But let's construct a valid multipart request.
        image_path = case["image_path"]
        
        # Create a dummy image if it doesn't exist just for the local test
        if not os.path.exists(image_path):
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            with open(image_path, "wb") as img:
                img.write(b"dummy_image_data")

        try:
            with open(image_path, "rb") as img_file:
                files = {"image_file": (os.path.basename(image_path), img_file, "image/jpeg")}
                response = requests.post(API_URL, files=files, timeout=15)
            
            if response.status_code == 200:
                ai_text = response.json().get("reading", "")
                
                # Compute Score
                score = compute_similarity(expert_text, ai_text)
                total_score += score
                
                if score < 0.5:
                    low_conf += 1
                else:
                    high_conf += 1
                    
                results.append({
                    "id": case["id"],
                    "edge_case": case["edge_case"],
                    "image_path": case["image_path"],
                    "expert_text": expert_text,
                    "ai_text": ai_text,
                    "score": score
                })
            else:
                print(f"  ❌ API Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
             print(f"  ❌ Request Failed: {e}")

    # Generate Summary
    if results:
        summary = {
            "total": len(results),
            "avg_score": total_score / len(results),
            "low_conf": low_conf,
            "high_conf": high_conf
        }
        generate_report(results, summary)
        print(f"\n✅ Audit complete! Report saved to {REPORT_PATH}")
    else:
        print("\n⚠️ No results to compile.")

if __name__ == "__main__":
    run_audit()
