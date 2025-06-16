# 创建密钥库的步骤

## 1. 生成密钥库（在项目根目录下运行）
# Windows PowerShell 或 CMD:
keytool -genkey -v -keystore masgui-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias masgui

# 会提示输入：
# - 密钥库密码（记住这个密码）
# - 名字、组织等信息
# - 密钥密码（可以与密钥库密码相同）

## 2. 将密钥库文件移动到 android/app 目录
# 移动 masgui-release-key.jks 到 android/app/

## 3. 创建 key.properties 文件
# 在 android/ 目录下创建 key.properties 文件，内容如下：
# storePassword=<您的密钥库密码>
# keyPassword=<您的密钥密码>
# keyAlias=masgui
# storeFile=masgui-release-key.jks
