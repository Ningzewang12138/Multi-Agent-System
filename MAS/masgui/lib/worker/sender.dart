import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:masgui/worker/clients.dart';

import 'haptic.dart';
import 'setter.dart';
import '../main.dart';
import '../services/multi_agent_service.dart';
import '../services/local_rag_service.dart';
import '../services/unified_knowledge_base_service.dart';
import '../config/app_config.dart';
import '../config/app_mode.dart';
import '../services/internet/internet_chat_service.dart';

import 'package:masgui/l10n/gen/app_localizations.dart';

import 'package:ollama_dart/ollama_dart.dart' as llama;
import 'package:dartx/dartx.dart';
import 'package:uuid/uuid.dart';
// ignore: depend_on_referenced_packages
import 'package:flutter_chat_types/flutter_chat_types.dart' as types;
// import 'package:scroll_to_index/scroll_to_index.dart';

List<String> images = [];
Future<List<llama.Message>> getHistory([String? addToSystem]) async {
  var system = prefs?.getString("system") ??
      "You are a helpful assistant. Your name is Baymin.";
  if (prefs!.getBool("noMarkdown") ?? false) {
    system +=
        "\nYou must not use markdown or any other formatting language in any way!";
  }
  if (addToSystem != null) {
    system += "\n$addToSystem";
  }

  List<llama.Message> history = (prefs!.getBool("useSystem") ?? true)
      ? [llama.Message(role: llama.MessageRole.system, content: system)]
      : [];
  List<llama.Message> history2 = [];
  images = [];
  for (var i = 0; i < messages.length; i++) {
    if (jsonDecode(jsonEncode(messages[i]))["text"] != null) {
      history2.add(llama.Message(
          role: (messages[i].author.id == user.id)
              ? llama.MessageRole.user
              : llama.MessageRole.system,
          content: jsonDecode(jsonEncode(messages[i]))["text"],
          images: (images.isNotEmpty) ? images : null));
      images = [];
    } else {
      var uri = jsonDecode(jsonEncode(messages[i]))["uri"] as String;
      String content = (uri.startsWith("data:image/png;base64,"))
          ? uri.removePrefix("data:image/png;base64,")
          : base64.encode(await File(uri).readAsBytes());
      uri = uri.removePrefix("data:image/png;base64,");
      images.add(content);
    }
  }

  history.addAll(history2.reversed.toList());
  return history;
}

List getHistoryString([String? uuid]) {
  uuid ??= chatUuid!;
  List messages = [];
  for (var i = 0; i < (prefs!.getStringList("chats") ?? []).length; i++) {
    if (jsonDecode((prefs!.getStringList("chats") ?? [])[i])["uuid"] == uuid) {
      messages = jsonDecode(
          jsonDecode((prefs!.getStringList("chats") ?? [])[i])["messages"]);
      break;
    }
  }

  if (messages.isNotEmpty && messages[0]["role"] == "system") {
    messages.removeAt(0);
  }
  for (var i = 0; i < messages.length; i++) {
    if (messages[i]["type"] == "image") {
      messages[i] = {
        "role": messages[i]["role"]!,
        "content": "<${messages[i]["role"]} inserted an image>"
      };
    }
  }

  return messages;
}

Future<String> getTitleAi(List history) async {
  final generated = await BayminClient.generateChatCompletion(
    request: llama.GenerateChatCompletionRequest(
        model: model!,
        messages: [
          const llama.Message(
              role: llama.MessageRole.system,
              content:
                  "Generate a three to six word title for the conversation provided by the user. If an object or person is very important in the conversation, put it in the title as well; keep the focus on the main subject. You must not put the assistant in the focus and you must not put the word 'assistant' in the title! Do preferably use title case. Use a formal tone, don't use dramatic words, like 'mystery' Use spaces between words, do not use camel case! You must not use markdown or any other formatting language! You must not use emojis or any other symbols! You must not use general clauses like 'assistance', 'help' or 'session' in your title! \n\n~~User Introduces Themselves~~ -> User Introduction\n~~User Asks for Help with a Problem~~ -> Problem Help\n~~User has a _**big**_ Problem~~ -> Big Problem"),
          llama.Message(
              role: llama.MessageRole.user,
              content: "```\n${jsonEncode(history)}\n```")
        ],
        keepAlive: int.parse(prefs!.getString("keepAlive") ?? "300")),
  ).timeout(Duration(
      seconds:
          (10.0 * (prefs!.getDouble("timeoutMultiplier") ?? 1.0)).round()));
  var title = generated.message.content;
  title = title.replaceAll("\n", " ");

  var terms = [
    "\"",
    "'",
    "*",
    "_",
    ".",
    ",",
    "!",
    "?",
    ":",
    ";",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}"
  ];
  for (var i = 0; i < terms.length; i++) {
    title = title.replaceAll(terms[i], "");
  }

  title = title.replaceAll(RegExp(r'<.*?>', dotAll: true), "");
  if (title.split(":").length == 2) {
    title = title.split(":")[1];
  }

  while (title.contains("  ")) {
    title = title.replaceAll("  ", " ");
  }
  return title.trim();
}

Future<void> setTitleAi(List history) async {
  try {
    var title = await getTitleAi(history);
    var tmp = (prefs!.getStringList("chats") ?? []);
    for (var i = 0; i < tmp.length; i++) {
      if (jsonDecode((prefs!.getStringList("chats") ?? [])[i])["uuid"] ==
          chatUuid) {
        var tmp2 = jsonDecode(tmp[i]);
        tmp2["title"] = title;
        tmp[i] = jsonEncode(tmp2);
        break;
      }
    }
    prefs!.setStringList("chats", tmp);
  } catch (_) {}
}

Future<String> send(String value, BuildContext context, Function setState,
    {void Function(String currentText, bool done)? onStream,
    String? addToSystem}) async {
  selectionHaptic();
  setState(() {
    sendable = false;
  });

  // 修改检查逻辑
  if (AppModeManager.isMultiAgentMode) {
    // 多Agent模式不需要检查host
    print('Using Multi-Agent mode');
  } else if (AppModeManager.isInternetMode) {
    // Internet模式不需要检查host
    print('Using Internet mode');
  } else if (host == null) {
    // 只有Ollama模式才需要检查host
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(AppLocalizations.of(context)!.noHostSelected),
        showCloseIcon: true));
    if (onStream != null) {
      onStream("", true);
    }
    return "";
  }

  if (!chatAllowed || model == null) {
    if (model == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(AppLocalizations.of(context)!.noModelSelected),
          showCloseIcon: true));
    }
    if (onStream != null) {
      onStream("", true);
    }
    return "";
  }

  bool newChat = false;
  if (chatUuid == null) {
    newChat = true;
    chatUuid = const Uuid().v4();
    prefs!.setStringList(
        "chats",
        (prefs!.getStringList("chats") ?? []).append([
          jsonEncode({
            "title": AppLocalizations.of(context)!.newChatTitle,
            "uuid": chatUuid,
            "messages": []
          })
        ]).toList());
  }

  var history = await getHistory(addToSystem);

  history.add(llama.Message(
      role: llama.MessageRole.user,
      content: value.trim(),
      images: (images.isNotEmpty) ? images : null));
  messages.insert(
      0,
      types.TextMessage(
          author: user, id: const Uuid().v4(), text: value.trim()));

  saveChat(chatUuid!, setState);

  setState(() {});
  chatAllowed = false;

  String text = "";
  String newId = const Uuid().v4();

  // 判断使用哪种模式
  if (AppModeManager.isInternetMode) {
    // 使用Internet模式
    try {
      final selectedModel = prefs?.getString('selected_internet_model');
      if (selectedModel == null) {
        throw Exception('No internet model selected');
      }
      
      final storedKey = prefs?.getString(InternetChatService.getApiKeyStorageKey(selectedModel)) ?? '';
      final apiKey = InternetChatService.getApiKey(selectedModel, storedKey);
      if (apiKey.isEmpty) {
        throw Exception('API key not configured');
      }
      
      // 构建消息列表
      List<Map<String, String>> messageList = [];
      for (int i = 1; i < messages.length; i++) {
        var msg = messages[i];
        if (msg is types.TextMessage) {
          messageList.insert(0, {
            'role': msg.author == user ? 'user' : 'assistant',
            'content': msg.text,
          });
        }
      }
      messageList.add({'role': 'user', 'content': value.trim()});
      
      // 发送请求
      final service = InternetChatService();
      final response = await service.sendMessage(
        modelId: selectedModel,
        apiKey: apiKey,
        messages: messageList,
      );
      
      // 处理响应
      text = response['choices'][0]['message']['content'];
      messages.insert(
        0,
        types.TextMessage(
          author: assistant,
          id: newId,
          text: text,
        ),
      );
      
      if (onStream != null) {
        onStream(text, true);
      }
      
      setState(() {});
      heavyHaptic();
    } catch (e) {
      // 错误处理
      for (var i = 0; i < messages.length; i++) {
        if (messages[i].id == newId) {
          messages.removeAt(i);
          break;
        }
      }
      setState(() {
        chatAllowed = true;
        messages.removeAt(0);
        if (messages.isEmpty) {
          var tmp = (prefs!.getStringList("chats") ?? []);
          for (var i = 0; i < tmp.length; i++) {
            if (jsonDecode((prefs!.getStringList("chats") ?? [])[i])["uuid"] ==
                chatUuid) {
              tmp.removeAt(i);
              prefs!.setStringList("chats", tmp);
              break;
            }
          }
          chatUuid = null;
        }
      });
      // ignore: use_build_context_synchronously
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), showCloseIcon: true));
      return "";
    }
  } else if (AppModeManager.isMultiAgentMode) {
    try {
      // 使用多Agent系统发送消息
      final service = MultiAgentService();

      // 构建消息列表（不包括刚刚添加的当前消息）
      List<Map<String, String>> messageList = [];
      // 跳过第一条消息（刚刚添加的当前消息）
      for (int i = 1; i < messages.length; i++) {
        var msg = messages[i];
        if (msg is types.TextMessage) {
          messageList.insert(0, {
            'role': msg.author == user ? 'user' : 'assistant',
            'content': msg.text,
          });
        }
      }

      // 添加当前消息到列表末尾
      messageList.add({'role': 'user', 'content': value.trim()});

      // 发送请求
      Map<String, dynamic> response;
      if (useRAG && selectedKnowledgeBase != null) {
        // 检查是否是本地知识库
        final unifiedService = UnifiedKnowledgeBaseService();
        final allKbs = await unifiedService.getAllKnowledgeBases();
        final selectedKb = allKbs.firstWhere(
          (kb) => kb['id'] == selectedKnowledgeBase,
          orElse: () => {},
        );

        if (selectedKb['location'] == 'local') {
          // 使用本地RAG
          final localRagService = LocalRAGService();
          text = await localRagService.chatWithLocalRAG(
            query: value.trim(),
            knowledgeBaseId: selectedKnowledgeBase!,
            model: model,
          );

          // 创建响应格式以保持一致性
          response = {
            'choices': [
              {
                'message': {
                  'content': text,
                  'role': 'assistant',
                }
              }
            ]
          };
        } else {
          // 使用服务器RAG
          response = await service.sendRAGMessage(
            messageList,
            selectedKnowledgeBase!,
            model: model,
          );
        }
      } else {
        response = await service.sendMessage(
          messageList,
          model: model,
        );
      }

      // 处理响应
      final assistantMessage = response['choices'][0]['message'];
      text = assistantMessage['content'];

      // 添加AI响应到消息列表
      messages.insert(
        0,
        types.TextMessage(
          author: assistant,
          id: newId,
          text: text,
        ),
      );

      if (onStream != null) {
        onStream(text, true);
      }

      setState(() {});
      heavyHaptic();
    } catch (e) {
      // 错误处理
      for (var i = 0; i < messages.length; i++) {
        if (messages[i].id == newId) {
          messages.removeAt(i);
          break;
        }
      }
      setState(() {
        chatAllowed = true;
        messages.removeAt(0);
        if (messages.isEmpty) {
          var tmp = (prefs!.getStringList("chats") ?? []);
          for (var i = 0; i < tmp.length; i++) {
            if (jsonDecode((prefs!.getStringList("chats") ?? [])[i])["uuid"] ==
                chatUuid) {
              tmp.removeAt(i);
              prefs!.setStringList("chats", tmp);
              break;
            }
          }
          chatUuid = null;
        }
      });
      // ignore: use_build_context_synchronously
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), showCloseIcon: true));
      return "";
    }
  } else {
    // 使用原有的Ollama系统
    try {
      if ((prefs!.getString("requestType") ?? "stream") == "stream") {
        final stream = BayminClient.generateChatCompletionStream(
          request: llama.GenerateChatCompletionRequest(
              model: model!,
              messages: history,
              keepAlive: int.parse(prefs!.getString("keepAlive") ?? "300")),
        ).timeout(Duration(
            seconds: (30.0 * (prefs!.getDouble("timeoutMultiplier") ?? 1.0))
                .round()));

        await for (final res in stream) {
          text += (res.message.content);
          for (var i = 0; i < messages.length; i++) {
            if (messages[i].id == newId) {
              messages.removeAt(i);
              break;
            }
          }
          if (chatAllowed) return "";
          messages.insert(
              0, types.TextMessage(author: assistant, id: newId, text: text));
          //TODO: add functionality
          //
          // chatKey!.currentState!.scrollToMessage(messages[1].id,
          //     preferPosition: AutoScrollPosition.end);
          if (onStream != null) {
            onStream(text, false);
          }
          setState(() {});
          heavyHaptic();
        }
      } else {
        llama.GenerateChatCompletionResponse request;
        request = await BayminClient.generateChatCompletion(
          request: llama.GenerateChatCompletionRequest(
              model: model!,
              messages: history,
              keepAlive: int.parse(prefs!.getString("keepAlive") ?? "300")),
        ).timeout(Duration(
            seconds: (30.0 * (prefs!.getDouble("timeoutMultiplier") ?? 1.0))
                .round()));
        if (chatAllowed) return "";
        messages.insert(
            0,
            types.TextMessage(
                author: assistant, id: newId, text: request.message.content));
        text = request.message.content;
        setState(() {});
        heavyHaptic();
      }
    } catch (e) {
      for (var i = 0; i < messages.length; i++) {
        if (messages[i].id == newId) {
          messages.removeAt(i);
          break;
        }
      }
      setState(() {
        chatAllowed = true;
        messages.removeAt(0);
        if (messages.isEmpty) {
          var tmp = (prefs!.getStringList("chats") ?? []);
          for (var i = 0; i < tmp.length; i++) {
            if (jsonDecode((prefs!.getStringList("chats") ?? [])[i])["uuid"] ==
                chatUuid) {
              tmp.removeAt(i);
              prefs!.setStringList("chats", tmp);
              break;
            }
          }
          chatUuid = null;
        }
      });
      // ignore: use_build_context_synchronously
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content:
              // ignore: use_build_context_synchronously
              Text(
                  AppLocalizations.of(context)!.settingsHostInvalid("timeout")),
          showCloseIcon: true));
      return "";
    }
  }

  // 共同的收尾处理
  saveChat(chatUuid!, setState);

  if (newChat && (prefs!.getBool("generateTitles") ?? true)) {
    void setTitle() async {
      await setTitleAi(getHistoryString());
      setState(() {});
    }

    setTitle();
  }

  setState(() {});
  chatAllowed = true;
  return text;
}
