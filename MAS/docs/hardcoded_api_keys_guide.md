# 硬编码API密钥配置指南

## 配置位置

在文件 `lib/services/internet/internet_chat_service.dart` 中找到以下代码：

```dart
// 硬编码的API密钥 - 请在这里填入您的API密钥
static const Map<String, String> _hardcodedApiKeys = {
  'deepseek-v3': '',  // 在这里填入您的DeepSeek API密钥
  'deepseek-r1': '',  // 在这里填入您的DeepSeek API密钥（通常与v3相同）
  'claude-4-sonnet': '',  // 在这里填入您的Claude API密钥
  'chatgpt-4o': '',  // 在这里填入您的ChatGPT API密钥
};
```

## 配置步骤

1. **获取API密钥**
   - DeepSeek: https://platform.deepseek.com/
   - Claude: https://console.anthropic.com/
   - ChatGPT: https://platform.openai.com/

2. **填入密钥**
   ```dart
   static const Map<String, String> _hardcodedApiKeys = {
     'deepseek-v3': 'sk-xxxxxxxxxxxxxxxx',  // 您的实际密钥
     'deepseek-r1': 'sk-xxxxxxxxxxxxxxxx',  // 同上
     'claude-4-sonnet': 'sk-ant-xxxxxxxxxx',  // Claude密钥
     'chatgpt-4o': 'sk-xxxxxxxxxxxxxxxx',  // OpenAI密钥
   };
   ```

3. **重新编译应用**
   ```bash
   cd masgui
   flutter clean
   flutter pub get
   flutter run
   ```

## 使用效果

- 配置硬编码密钥后，在模式选择界面会显示"Already configured"
- 用户仍可以通过点击"Change"按钮覆盖硬编码的密钥
- 优先使用硬编码密钥，其次使用用户输入的密钥

## 注意事项

1. **安全性**：硬编码密钥只适合个人使用，不要将包含密钥的代码提交到公开仓库
2. **备份密钥**：建议在安全的地方保存一份密钥备份
3. **定期更新**：如果密钥泄露或过期，及时更新

## Internet模式界面显示

在Internet模式下，应用会在顶部显示：
- 地球图标 🌐 表示正在使用Internet模式
- 当前选择的模型名称（如"DeepSeek V3"而不是内部ID）
