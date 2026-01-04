## TÍCH HỢP TRUY XUẤT NGUỒN GỐC CHUỖI CUNG ỨNG TRÊN NỀN TẢNG ODOO VÀ HYPERLEDGER BESU

## 1. GIỚI THIỆU CHUNG

Dự án này tập trung phát triển một giải pháp tích hợp công nghệ **Blockchain** vào hệ thống quản trị nguồn lực doanh nghiệp **Odoo ERP** nhằm phục vụ bài toán **truy xuất nguồn gốc chuỗi cung ứng**.

Mục tiêu của hệ thống là ghi nhận một cách **bất biến (immutable)** các dữ liệu quan trọng trong quá trình vận hành, bao gồm:

* Lệnh sản xuất (Manufacturing Orders)
* Dịch chuyển kho (Stock Pickings)

Thay vì lưu toàn bộ dữ liệu nghiệp vụ lên Blockchain, hệ thống thực hiện:

* Chuẩn hóa dữ liệu
* Băm dữ liệu (hash)
* Ghi nhận hash và metadata lên **Private Blockchain** sử dụng **Hyperledger Besu**

Cách tiếp cận này đảm bảo:

* Tính minh bạch
* Khả năng kiểm toán
* Chống sửa đổi dữ liệu
* Không làm lộ dữ liệu nội bộ doanh nghiệp

---

## 2. KIẾN TRÚC TỔNG THỂ

Trong kiến trúc hệ thống:

* **Hyperledger Besu**: Mạng Blockchain riêng (Private Blockchain)
* **Smart Contract**: Định nghĩa logic ghi nhận truy xuất nguồn gốc
* **Odoo ERP**: Client, chịu trách nhiệm ký và gửi giao dịch Blockchain

Luồng dữ liệu tổng quát:

```
Odoo (web3.py)
   ↓ ký giao dịch
Smart Contract (Besu)
   ↓ ghi log bất biến
Blockchain Ledger
```

⚠️ Do đó, **hạ tầng Blockchain và Smart Contract bắt buộc phải được triển khai trước khi cấu hình Odoo**.

---

## 3. CHUẨN BỊ HẠ TẦNG BLOCKCHAIN (YÊU CẦU TIÊN QUYẾT)

### 3.1. Triển khai mạng Hyperledger Besu

Quy trình thiết lập node Besu, genesis file và khởi chạy mạng Private Blockchain đã được tài liệu hóa chi tiết tại repository:

```
https://github.com/tqt2404/besu-network
```

Sau khi mạng Besu hoạt động, cần xác định:

* RPC Endpoint (ví dụ: `http://127.0.0.1:8545`)
* Chain ID của mạng lưới
* Tài khoản có quyền deploy Smart Contract

---

### 3.2. Triển khai Smart Contract bằng Hardhat

Sau khi deploy thành công:

* **Lưu lại Contract Address** hiển thị trên terminal
* **Lưu nội dung ABI** trong file:

```
artifacts/contracts/tên_smart_contract.sol/tên_smart_contract.json
```

Hai thông tin này sẽ được sử dụng để cấu hình Odoo.

---

## 4. CÀI ĐẶT VÀ TRIỂN KHAI ODOO

### 4.1. Cài đặt PostgreSQL

```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-client
```

Tạo user database cho Odoo:

```bash
sudo su - postgres
createuser -s odoo
exit
```

---

### 4.2. Chuẩn bị mã nguồn

```bash
mkdir odoo-project
cd odoo-project

git clone https://github.com/odoo/odoo.git --depth 1 --branch 17.0 --single-branch odoo
git clone https://github.com/tqt2404/odoo-blockchain-integration.git custom_addons
```

---

### 4.3. Thiết lập môi trường Python

```bash
sudo apt install python3-venv python3-dev libpq-dev build-essential
python3 -m venv venv
source venv/bin/activate
```

---

### 4.4. Cài đặt thư viện phụ thuộc

```bash
pip install --upgrade pip
pip install -r odoo/requirements.txt
pip install web3==6.0.0
```

---

### 4.5. Cấu hình Odoo

File `odoo.conf`:

```ini
[options]
admin_passwd = admin
http_port = 8069
db_host = False
db_port = False
db_user = odoo
db_password = False
addons_path = /abs/path/odoo/addons,/abs/path/custom_addons
```

---

### 4.6. Khởi chạy hệ thống

```bash
python3 odoo/odoo-bin -c odoo.conf
```

---

## 5. CẤU HÌNH BLOCKCHAIN TRONG ODOO

### 5.1. Tạo Blockchain Connector

Vào menu:

```
Blockchain > Configuration > Connectors
```

Tạo mới:

* Name: ví dụ `Besu Private Network`
* Service URL: `http://127.0.0.1:8545`
* Chain ID: `1337`

Lưu lại.

---

### 5.2. Tạo Ví Blockchain (Account)

Hệ thống sử dụng ví quản trị (ví dụ `AdminWallet`) để ký giao dịch.

Thực hiện:

```
Blockchain > Accounts
```

Tạo mới Account:

* Name: tùy ý (ví dụ `AdminWallet`)
* Connector: `Besu Private Network`

Sau khi lưu, bấm **Generate Account**.

Khi popup yêu cầu mật khẩu xuất hiện, nhập mật khẩu (ví dụ: `admin`).

Sau khi tạo thành công, hệ thống sinh ra:

* Address
* Encrypted Key

⚠️ Cần nạp coin native (ETH) vào địa chỉ này để trả phí gas.

---

### 5.3. Cấu hình Smart Contract

Vào menu:

```
Blockchain > Smart Contracts
```

Tạo mới:

* Name: Tên smart contract
* Connector: ví dụ chọn `Besu Private Network`
* Address: Dán **Contract Address** đã deploy bằng Hardhat
* ABI: Dán **toàn bộ nội dung JSON ABI** từ file artifacts

Lưu lại để hoàn tất cấu hình.

---

## 6. VẬN HÀNH VÀ DEMO

Sau khi cấu hình hoàn tất:

* Khi **xác nhận lệnh sản xuất (Mark as Done)**
* Khi **xác nhận dịch chuyển kho (Validate)**

Hệ thống sẽ:

* Chuẩn hóa dữ liệu
* Tạo hash
* Gọi hàm Smart Contract
* Ghi nhận TxHash trên Blockchain

TxHash được hiển thị trực tiếp trên giao diện Odoo, cho phép đối soát và kiểm toán độc lập.
