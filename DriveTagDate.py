import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Thử đọc secrets
try:
    creds_dict = dict(st.secrets["gcp_service_account"])
    st.success("✅ Đọc được secrets['gcp_service_account']")
except Exception as e:
    st.error("❌ Không đọc được secrets['gcp_service_account']")
    st.exception(e)
    st.stop()

# Tạo credentials từ dict
try:
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    st.success("✅ Tạo credentials thành công")
except Exception as e:
    st.error("❌ Lỗi khi tạo credentials")
    st.exception(e)
    st.stop()

# Kiểm tra Google Drive API hoạt động
try:
    drive_service = build("drive", "v3", credentials=credentials)
    results = drive_service.files().list(pageSize=5).execute()
    files = results.get("files", [])

    st.success("✅ Gọi Google Drive API thành công")
    for file in files:
        st.write(f"- {file['name']} ({file['id']})")
except Exception as e:
    st.error("❌ Gọi API thất bại")
    st.exception(e)
