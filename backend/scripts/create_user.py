# Tao user thu cong - dung cho admin dau tien vi khong co route dang ky cong
# khai cho role admin (tranh tu leo thang quyen).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import user_store

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Cách dùng: python create_user.py <username> <password> [role]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else "user"

    user_store.create_user(username, password, role)
    print(f"Đã tạo user '{username}' với role '{role}'.")
