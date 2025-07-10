import streamlit as st
from google.oauth2 import service_account

st.title("🔐 Kiểm tra Google Credentials")

try:
    # Ép kiểu về dict chuẩn
    creds_dict = dict(st.secrets["gcp_service_account"])

    # Tạo credentials
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    st.success("✅ Tạo credentials thành công!")
    st.code(str(credentials.service_account_email), language="python")

except Exception as e:
    st.error("❌ Lỗi khi tạo credentials:")
    st.exception(e)
