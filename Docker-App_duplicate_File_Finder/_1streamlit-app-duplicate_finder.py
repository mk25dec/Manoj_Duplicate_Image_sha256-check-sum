# _1streamlit-app-duplicateFinder.py

"""
What:
streamlit app
To compare 2 or more folders to find duplicate files.
it gives suggestion to delete/ rm commands for cleanup to keep original file and delete duplicates

How to Run:
source /Users/manoj/coding/Env/venv-python/bin/activate
cd /Users/manoj/coding/scripts/prod
streamlit run _1streamlit-app-duplicate_finder.py

Logic: Used sha256 check sum of file
"""
# _1streamlit-app-duplicateFinder.py

import streamlit as st
import os
import base64
from collections import defaultdict
from datetime import datetime
from _1streamlit_duplicate_finder_logic import find_duplicate_files # Import our backend logic


# --- Graceful Library Imports for Optional Features ---
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

st.set_page_config(layout="wide", page_title="Duplicate File Finder")

# --- Define a robust path to the assets folder ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "file_icon.png")

# --- Define supported image extensions for previews ---
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')

# --- Helper Functions (Stable) ---
def update_keep_list(hash_val, path):
    files_to_keep = st.session_state.files_to_keep.get(hash_val, set())
    if path in files_to_keep:
        files_to_keep.discard(path)
    else:
        files_to_keep.add(path)
    st.session_state.files_to_keep[hash_val] = files_to_keep
    st.session_state.selection_mode = "Manual Selection"

def display_sidebar_preview():
    st.subheader("File Preview")
    filepath = st.session_state.preview_path
    try:
        st.image(filepath, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load preview: {e}")
    if st.button("Close Preview", use_container_width=True):
        del st.session_state.preview_path
        st.rerun()

def apply_selection_logic():
    if not st.session_state.get('scan_completed'):
        return
    duplicates = st.session_state.get('duplicates', {})
    if not duplicates:
        return
    mode = st.session_state.get('selection_mode')
    if mode == "Auto-select (Keep shortest path)":
        for hash_val, data in duplicates.items():
            path_to_keep = min(data['paths'], key=len)
            st.session_state.files_to_keep[hash_val] = {path_to_keep}
    elif mode == "Manual Selection":
        st.session_state.files_to_keep = defaultdict(set)

def generate_scan_report():
    report_lines = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines.append(f"Duplicate File Scan Report\nGenerated on: {timestamp}\n" + "=" * 40)
    duplicates = st.session_state.get('duplicates', {})
    files_to_keep = st.session_state.get('files_to_keep', {})
    if not duplicates:
        report_lines.append("No duplicate files were found.")
        return "\n".join(report_lines)
    for i, (hash_val, data) in enumerate(duplicates.items(), 1):
        report_lines.append(f"\n--- Set {i} | Hash: {hash_val} ---")
        kept_in_set = files_to_keep.get(hash_val)
        if not kept_in_set:
            report_lines.append("  [UNREVIEWED] This set has not been reviewed.")
            for path in sorted(data['paths']):
                report_lines.append(f"    - {path}")
            continue
        for path in sorted(data['paths']):
            status = "[KEEP]" if path in kept_in_set else "[DELETE]"
            report_lines.append(f"  {status} {path}")
    return "\n".join(report_lines)

def format_bytes(byte_count):
    if byte_count is None or byte_count == 0:
        return "0 B"
    power, n = 1024, 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while byte_count >= power and n < len(power_labels) - 1:
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}"

# --- UPDATED STATS CALCULATION FUNCTION ---
def calculate_cleanup_stats():
    """Calculates the number of files to keep/delete and space saved."""
    total_files_found = 0
    files_to_delete = 0
    files_to_keep = 0
    space_saved = 0
    
    duplicates = st.session_state.get('duplicates', {})
    selections = st.session_state.get('files_to_keep', {})

    for hash_val, data in duplicates.items():
        num_in_set = len(data['paths'])
        file_size = data['size']
        
        total_files_found += num_in_set
        
        kept_in_set = selections.get(hash_val, set())
        num_kept = len(kept_in_set)
        num_to_delete = num_in_set - num_kept

        files_to_keep += num_kept
        files_to_delete += num_to_delete
        space_saved += num_to_delete * file_size
        
    return total_files_found, files_to_keep, files_to_delete, space_saved

# --- Initialize Session State ---
if 'selection_mode' not in st.session_state: st.session_state.selection_mode = "Manual Selection"
if 'scan_completed' not in st.session_state: st.session_state.scan_completed = False
if 'files_to_keep' not in st.session_state: st.session_state.files_to_keep = defaultdict(set)

# --- Main UI ---
st.title("Duplicate File Finder")

# --- UPDATED: CSS to restore green button styles ---
st.markdown("""
<style>
    div[data-testid="stTabs"] img {
        image-rendering: -webkit-crisp-edges; image-rendering: -moz-crisp-edges; image-rendering: crisp-edges;
        object-fit: contain;
    }
    button[role="tab"] p { font-size: 16px; }
    button[title="View fullscreen"] { display: none; }
    .code-block { padding: 0.25rem 0.5rem; border-radius: 0.25rem; border: 1px solid #444; font-family: monospace; white-space: pre-wrap; word-break: break-all; font-size: 12px; }
    .keep-block { background-color: rgba(40, 167, 69, 0.2); }
    .delete-block { background-color: rgba(220, 53, 69, 0.2); }
    
    /* This class styles both the Start and Download buttons to be identical */
    .st-green-button button {
        background-color: #28a745 !important;
        color: white !important;
        border-color: #28a745 !important;
    }
    .st-green-button button:hover {
        background-color: #218838 !important;
        color: white !important;
        border-color: #218838 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.header("Scan Configuration")
    st.radio(
        "**Selection Mode**", ("Manual Selection", "Auto-select (Keep shortest path)"),
        key='selection_mode', help="Choose how selections are made. You can change this anytime after a scan is complete.",
        on_change=apply_selection_logic
    )
    if st.session_state.selection_mode == "Manual Selection":
        st.info("You will select files to KEEP.", icon="✍️")
    else:
        st.info("System will auto-select files to KEEP ie. files with shortest path.", icon="🤖")
    
    folder_paths_input = st.text_area("Folders to Scan (one per line):", height=70)
    exclude_paths_input = st.text_area("Folders to Exclude (one per line):", height=70)
    
    # --- UPDATED: Start Scan button wrapped in custom class ---
    st.markdown('<div class="st-green-button">', unsafe_allow_html=True)
    if st.button("🚀 Start Scan", use_container_width=True, type="primary" ): # Note: type="primary" is removed
        keys_to_keep_state = ['selection_mode']
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep_state: del st.session_state[key]
        st.session_state.files_to_keep = defaultdict(set)
        include_folders = [p.strip() for p in folder_paths_input.split('\n') if p.strip()]
        valid_folders = [p for p in include_folders if os.path.isdir(p)]
        exclude_folders = [p.strip() for p in exclude_paths_input.split('\n') if p.strip()]
        if not valid_folders:
            st.error("Please provide at least one valid folder to scan.")
        else:
            with st.spinner("Scanning... This may take a while for large directories..."):
                st.session_state.duplicates = find_duplicate_files(valid_folders, exclude_folders)
                st.session_state.scan_completed = True
                apply_selection_logic()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    #st.divider()


    # --- UPDATED: Download Report button green color wrapped in custom class ---
    st.markdown("""
        <style>
            div.stDownloadButton > button {
                background-color: #4CAF50 !important;
                color: white !important;
                border: none !important;
            }
            div.stDownloadButton > button:hover {
                background-color: #45a049 !important;
            }
        </style>
        """, unsafe_allow_html=True)

    if st.session_state.get('scan_completed', False):
        st.download_button(
            label="📄 Download Scan Report",
            data=generate_scan_report(),
            file_name=f"duplicate_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
            type="secondary"  # 🔑 Required for CSS to work
        )
        
    if "preview_path" in st.session_state:
        display_sidebar_preview()

# --- Display Results ---
if st.session_state.get('scan_completed', False):
    duplicates = st.session_state.get('duplicates', {})
    if not duplicates:
        st.success("🎉 Hooray! No duplicate files were found.")
    else:
        # --- NEW REORGANIZED DASHBOARD LAYOUT ---
        # Header Section
        st.header("Found Duplicate Files", divider="rainbow")

        # Calculate stats
        total_found, to_keep, to_delete, space_saved = calculate_cleanup_stats()

        # Create metrics in a single row under the header
        metric_cols = st.columns(5)
        metric_cols[0].metric("Total Files", total_found)
        metric_cols[1].metric("Files to Keep", to_keep)
        metric_cols[2].metric("Files to Delete", to_delete, delta_color="inverse")
        metric_cols[3].metric("Space Saved", format_bytes(space_saved))
        metric_cols[4].metric("Duplicate Sets", len(duplicates))

        # Optional: Add some spacing
        #st.subheader("", divider="rainbow")  # Standalone rainbow divider
        #st.write("---" )  # Horizontal line separator

        unreviewed_count = len([h for h, data in duplicates.items() if not st.session_state.files_to_keep.get(h)])
        tab1_label = "✍️ Review & Select Files"
        tab2_label = f"🗑️ Generate Deletion Script (✅ {to_delete} files)" if unreviewed_count == 0 else f"🗑️ Generate Deletion Script \t (⚠️ {unreviewed_count} unreviewed)"
        tab1, tab2 = st.tabs([tab1_label, tab2_label])

        with tab1:
            st.info("Click the icon to toggle between Keep (✅) or Delete (❌).", icon="ℹ️")
            for i, (hash_val, data) in enumerate(duplicates.items(), 1):
                paths = data['paths']
                st.write(f"**Set {i}** ({len(paths)} files) — Hash: `{hash_val[:12]}...`")
                layout_cols = st.columns([2, 5])
                with layout_cols[0]:
                    thumb_path = paths[0]
                    with st.container():
                        file_ext = os.path.splitext(thumb_path)[1].lower()
                        image_to_display = thumb_path if file_ext in IMAGE_EXTENSIONS else ICON_PATH
                        st.image(image_to_display, width=100)
                        if file_ext in IMAGE_EXTENSIONS:
                            st.button("🔎", key=f"preview_set_{hash_val}", on_click=lambda p=thumb_path: st.session_state.update(preview_path=p), help="Preview this set in the sidebar")
                            st.markdown(f'<style>div[data-testid="stButton"]>button[data-key="preview_set_{hash_val}"]{{position:absolute;top:4px;right:4px;background-color:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.6);border-radius:50%;width:28px;height:28px;color:white;}}div[data-testid="stButton"]>button[data-key="preview_set_{hash_val}"]:hover{{background-color:rgba(0,0,0,0.7);border-color:white;}}</style>', unsafe_allow_html=True)
                with layout_cols[1]:
                    files_kept_in_set = st.session_state.files_to_keep.get(hash_val, set())
                    for path in sorted(paths):
                        is_kept = path in files_kept_in_set
                        file_cols = st.columns([1, 10, 2])
                        with file_cols[0]:
                            st.button("✅" if is_kept else "❌", key=f"toggle_{path}", on_click=update_keep_list, args=(hash_val, path))
                        with file_cols[1]:
                            st.markdown(f'<div class="code-block {"keep-block" if is_kept else "delete-block"}">{path}</div>', unsafe_allow_html=True)
                        with file_cols[2]:
                            if PYPERCLIP_AVAILABLE:
                                action_cols = st.columns(2)
                                action_cols[0].button("📝", key=f"copy_file_{path}", help="Copy File Path", use_container_width=True, on_click=lambda p=path: pyperclip.copy(p) or st.toast("Copied file path!"))
                                action_cols[1].button("📁", key=f"copy_folder_{path}", help="Copy Folder Path", use_container_width=True, on_click=lambda d=os.path.dirname(path): pyperclip.copy(d) or st.toast("Copied folder path!"))
        with tab2:
            st.header("Deletion Shell Script")
            st.warning("🚨 **CRITICAL:** Review these commands carefully before running.", icon="⚠️")
            if unreviewed_count > 0:
                with st.expander(f"Unreviewed Sets ({unreviewed_count})", expanded=False):
                    st.warning("Safety Switch: No deletion commands will be generated for below sets, because you decided to DELETE ALL files for below sets, without keeping atleast 1 copy", icon="ℹ️")
                    for i, (hash_val, data) in enumerate(duplicates.items(), 1):
                        if not st.session_state.files_to_keep.get(hash_val):
                            display_list = [f"Set {i} (hash: {hash_val[:12]}...)"]
                            for path in sorted(data['paths']): display_list.append(f"  {path}")
                            st.code("\n".join(display_list), language='text')
            all_commands = []
            if to_delete > 0:
                expander_label = f"Reviewed Sets: Generated Deletion Commands ({to_delete} files to delete)"
                with st.expander(expander_label, expanded=True):
                    for i, (hash_val, data) in enumerate(duplicates.items(), 1):
                        files_kept = st.session_state.files_to_keep.get(hash_val, set())
                        if not files_kept: continue
                        files_to_delete_list = set(data['paths']) - files_kept
                        if files_to_delete_list:
                            all_commands.append(f"# Set {i}: {hash_val[:12]}...")
                            for path in sorted(list(files_to_delete_list)): all_commands.append(f'rm "{path}"')
                            all_commands.append("")
                    st.code("\n".join(all_commands), language="shell")
                    st.download_button("Download Deletion Script (.sh)", data="\n".join(all_commands), file_name="delete_duplicates.sh", mime="text/x-shellscript", use_container_width=True)
            if to_delete == 0 and unreviewed_count == 0:
                st.info("No files are currently marked for deletion.")