import os
import shutil

assets_dir = r"h:\Kaggle Project\aquaguard-agent\assets"
os.makedirs(assets_dir, exist_ok=True)

banner_src = r"C:\Users\harsh\.gemini\antigravity-ide\brain\62a84dd7-5a20-441f-aafb-c3950bfca70a\aquaguard_cover_banner_1782486282495.png"
banner_dst = os.path.join(assets_dir, "cover_page_banner.png")

diagram_src = r"C:\Users\harsh\.gemini\antigravity-ide\brain\62a84dd7-5a20-441f-aafb-c3950bfca70a\aquaguard_architecture_diagram_1782486308379.png"
diagram_dst = os.path.join(assets_dir, "architecture_diagram.png")

try:
    shutil.copy2(banner_src, banner_dst)
    shutil.copy2(diagram_src, diagram_dst)
    print("✅ Success! Images have been copied to the assets folder.")
except Exception as e:
    print(f"❌ Error copying images: {e}")
