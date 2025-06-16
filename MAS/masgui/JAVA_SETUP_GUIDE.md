# 设置 Java 环境变量指南

## Windows 11/10 设置步骤：

1. **右键点击"此电脑"** → **属性**
2. **高级系统设置** → **环境变量**

3. **在系统变量中添加**：
   - 变量名：`JAVA_HOME`
   - 变量值：`C:\Program Files\Java\jdk-17` (您的 JDK 安装路径)

4. **编辑 Path 变量**：
   - 找到 `Path` 变量
   - 点击"编辑"
   - 添加新条目：`%JAVA_HOME%\bin`

5. **确认保存所有对话框**

## 快速设置（命令行）：

以管理员身份运行 CMD，执行：

```cmd
setx JAVA_HOME "C:\Program Files\Java\jdk-17" /M
setx Path "%Path%;%JAVA_HOME%\bin" /M
```

## 验证安装：

打开新的命令提示符窗口，运行：

```cmd
echo %JAVA_HOME%
java -version
javac -version
```

如果都显示正确的版本信息，说明配置成功！
