import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import sqlite3
import pandas as pd
import tempfile
import io
import os

# --- Setup Google Drive API ---
# Tạo credentials từ secrets
creds_dict = dict(st.secrets["gcp_service_account"])
credentials = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=['https://www.googleapis.com/auth/drive']
)

drive_service = build('drive', 'v3', credentials=credentials)

# --- Drive DB Sync Helpers ---
def find_or_create_db_file(drive_service, filename, folder_id=None):
    query = f"name='{filename}' and mimeType='application/octet-stream'"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]['id']
    media = MediaIoBaseUpload(io.BytesIO(b""), mimetype="application/octet-stream")
    file_metadata = {"name": filename, "parents": [folder_id] if folder_id else []}
    created = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return created['id']

def download_db_to_tempfile(drive_service, file_id):
    fh = tempfile.NamedTemporaryFile(delete=False)
    downloader = MediaIoBaseDownload(fh, drive_service.files().get_media(fileId=file_id))
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return fh.name

def upload_db_from_tempfile(drive_service, file_id, local_path):
    with open(local_path, "rb") as f:
        media = MediaIoBaseUpload(f, mimetype="application/octet-stream", resumable=True)
        drive_service.files().update(fileId=file_id, media_body=media).execute()

# --- Tag DB Logic ---
db_drive_id = find_or_create_db_file(drive_service, DB_FILENAME, folder_id=DRIVE_FOLDER_ID)
temp_db_path = download_db_to_tempfile(drive_service, db_drive_id)

def load_tags_from_db():
    try:
        conn = sqlite3.connect(temp_db_path)
        df = pd.read_sql_query("SELECT * FROM tags", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame(columns=["Name", "Archtype", "Description"])

def insert_tag_to_db(name, archtype, description):
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            Name TEXT,
            Archtype TEXT,
            Description TEXT
        )
    """)
    cursor.execute("INSERT INTO tags (Name, Archtype, Description) VALUES (?, ?, ?)",
                   (name, archtype, description))
    conn.commit()
    conn.close()
    upload_db_from_tempfile(drive_service, db_drive_id, temp_db_path)

# --- UI ---
st.set_page_config(page_title="Drive Folder + Tag Manager", layout="wide")
st.title("📁 Google Drive Folder Tool")

tab1, tab2 = st.tabs(["📂 Chọn thư mục hoặc file", "🏷️ Quản lý Tag"])

# --- Extract ID ---
def extract_id_from_url(url):
    if "folders/" in url:
        return url.split("folders/")[1].split("?")[0]
    elif "file/d/" in url:
        return url.split("file/d/")[1].split("/")[0]
    elif "id=" in url:
        return url.split("id=")[1].split("&")[0]
    return None

# --- Metadata ---
def get_file_metadata(file_id):
    return drive_service.files().get(
        fileId=file_id,
        fields="id, name, mimeType, description"
    ).execute()

def update_file_description(file_id, new_description):
    return drive_service.files().update(
        fileId=file_id,
        body={"description": new_description}
    ).execute()

# --- TAB 1 ---
with tab1:
    with st.sidebar:
        file_url = st.text_input("🔗 Nhập link file hoặc folder Google Drive:")

    if file_url:
        file_id = extract_id_from_url(file_url)
        if file_id:
            metadata = get_file_metadata(file_id)
            st.subheader("📂 Đối tượng đã chọn:")
            st.markdown(f"**Tên:** `{metadata['name']}`")
            st.markdown(f"🔍 **Loại:** `{metadata['mimeType']}`")
            st.markdown(f"📄 **Mô tả hiện tại:** `{metadata.get('description', '(trống)')}`")

            tag_df = load_tags_from_db()
            tag_choices = tag_df['Name'].tolist()

            with st.form("update_form"):
                date = st.date_input("📅 Ngày")
                selected_tags = st.multiselect("🏷️ Chọn tag", tag_choices)
                submitted = st.form_submit_button("Cập nhật mô tả")

                if submitted:
                    date_str = date.strftime("%d/%m/%Y")
                    tag_str = ", ".join(selected_tags)
                    new_description = f"date: {date_str}\ntag: {tag_str}"
                    update_file_description(file_id, new_description)
                    st.success("✅ Mô tả đã được cập nhật.")
                    st.code(new_description, language="markdown")
        else:
            st.error("❌ Không thể trích xuất ID từ link.")
    else:
        st.info("🔎 Vui lòng nhập link ở sidebar.")

# --- TAB 2 ---
with tab2:
    st.subheader("🏷️ Danh sách Tag hiện có")
    df = load_tags_from_db()
    st.dataframe(df, use_container_width=True)

    st.markdown("### ➕ Thêm tag mới")
    existing_archtypes = sorted(df['Archtype'].dropna().unique().tolist())

    with st.form("add_tag_form"):
        name = st.text_input("Tên Tag")

        col1, col2 = st.columns(2)
        with col1:
            archtype_select = st.selectbox("Chọn Archtype có sẵn", options=existing_archtypes)
        with col2:
            archtype_manual = st.text_input("Hoặc nhập Archtype mới")

        description = st.text_area("Mô tả")
        add_submitted = st.form_submit_button("Thêm vào DB")

        if add_submitted:
            if not name.strip():
                st.warning("⚠️ Tên tag không được để trống.")
            else:
                archtype_final = archtype_manual.strip() if archtype_manual.strip() else archtype_select.strip()
                insert_tag_to_db(name.strip(), archtype_final, description.strip())
                st.success(f"✅ Đã thêm tag `{name.strip()}` với archtype `{archtype_final}`.")
                st.rerun()
