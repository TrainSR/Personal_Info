import streamlit as st
from google.oauth2 import service_account

st.title("🔐 Kiểm tra GCP Credentials")

try:
    # Truy cập đúng section
    gcp_secrets = st.secrets["gcp_service_account"]
    
    # Chuyển sang dict để dùng với from_service_account_info
    creds_dict = {k: gcp_secrets[k] for k in gcp_secrets}
    
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    st.success("✅ Tạo credentials thành công!")
    st.write("📧 Email:", credentials.service_account_email)

except Exception as e:
    st.error("❌ Không thể tạo credentials:")
    st.exception(e)
