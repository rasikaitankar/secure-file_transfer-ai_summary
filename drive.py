"""
utils/drive.py
--------------
Google Drive Cloud Storage Module

HOW TO ENABLE:
1. Go to https://console.cloud.google.com
2. Create a project → Enable "Google Drive API"
3. Create credentials → OAuth 2.0 Client ID → Desktop App
4. Download credentials.json → place in project root
5. pip install PyDrive
6. Set ENABLE_DRIVE = True in app.py

NETWORKING CONCEPT — Cloud Networking:
  Instead of storing encrypted files on the local server disk,
  they are uploaded to Google Drive via HTTPS API calls.
  This demonstrates:
  - Cloud Storage architecture
  - REST API calls from server to external cloud service
  - OAuth 2.0 authentication flow
  - Files accessible from any location (not just local disk)
"""

import os

try:
    from pydrive.auth import GoogleAuth
    from pydrive.drive import GoogleDrive
    PYDRIVE_AVAILABLE = True
except ImportError:
    PYDRIVE_AVAILABLE = False
    print("[DRIVE] ⚠️  PyDrive not installed. Run: pip install PyDrive")


# Shared Drive client (initialized once)
_drive = None
DRIVE_FOLDER_NAME = "SecureFileShare_Encrypted"


def _get_drive():
    """Initialize and return authenticated Google Drive client."""
    global _drive
    if _drive is not None:
        return _drive

    if not PYDRIVE_AVAILABLE:
        raise RuntimeError("PyDrive not installed. Run: pip install PyDrive")

    if not os.path.exists("credentials.json"):
        raise FileNotFoundError(
            "credentials.json not found.\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials.\n"
            "See utils/drive.py for full setup instructions."
        )

    gauth = GoogleAuth()
    # Try to load saved credentials
    gauth.LoadCredentialsFile("models/drive_credentials.json")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("models/drive_credentials.json")

    _drive = GoogleDrive(gauth)
    print("[DRIVE] ✅ Authenticated with Google Drive")
    return _drive


def _get_or_create_folder(drive) -> str:
    """Get (or create) the SecureFileShare folder on Google Drive. Returns folder ID."""
    query = f"title='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()
    if file_list:
        return file_list[0]['id']

    folder = drive.CreateFile({
        'title': DRIVE_FOLDER_NAME,
        'mimeType': 'application/vnd.google-apps.folder'
    })
    folder.Upload()
    print(f"[DRIVE] ✅ Created folder '{DRIVE_FOLDER_NAME}' on Google Drive")
    return folder['id']


def upload_to_drive(local_path: str, filename: str) -> str:
    """
    Upload an encrypted file to Google Drive.

    Args:
        local_path: Path to the local .enc file
        filename:   Name to give the file on Drive

    Returns:
        Google Drive file ID (stored in metadata for later download)

    NETWORKING NOTE:
        This function makes HTTPS POST requests to the Google Drive API.
        The encrypted file bytes travel over TLS — doubly secure:
        file is AES-encrypted AND transmitted over HTTPS.
    """
    drive     = _get_drive()
    folder_id = _get_or_create_folder(drive)

    gfile = drive.CreateFile({
        'title':   filename,
        'parents': [{'id': folder_id}]
    })
    gfile.SetContentFile(local_path)
    gfile.Upload()

    print(f"[DRIVE] ✅ Uploaded '{filename}' to Google Drive (ID: {gfile['id']})")
    return gfile['id']


def download_from_drive(drive_file_id: str, local_path: str) -> None:
    """
    Download an encrypted file from Google Drive to local path.

    Args:
        drive_file_id: Google Drive file ID (from metadata)
        local_path:    Where to save the downloaded file locally

    NETWORKING NOTE:
        This is an HTTPS GET request to the Google Drive API.
        The file travels encrypted (TLS) from Google's servers to ours.
    """
    drive = _get_drive()
    gfile = drive.CreateFile({'id': drive_file_id})
    gfile.GetContentFile(local_path)
    print(f"[DRIVE] ✅ Downloaded file ID '{drive_file_id}' → '{local_path}'")
