import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';

import 'package:masgui/l10n/gen/app_localizations.dart';

import 'screen_settings.dart';
import 'screen_voice.dart';
// import 'screen_welcome.dart';  // 不再需要欢迎屏幕
import 'screens/knowledge_base_screen.dart';
import 'screens/device_knowledge_base_screen.dart';
import 'screens/unified_knowledge_base_screen.dart';
import 'services/unified_knowledge_base_service.dart';
import 'services/device_id_service.dart';
import 'screens/sync/knowledge_sync_screen.dart';
import 'services/multi_agent_service.dart';
import 'services/sync/device_discovery_service.dart';
import 'services/sync/simple_device_broadcast_service.dart';
import 'screens/mcp/mcp_service_list_screen.dart';
import 'services/mcp/mcp_service.dart';
import 'config/app_config.dart';
import 'config/icon_sizes.dart';
import 'config/logo_animation_config.dart';
import 'utils/responsive_helper.dart';
import 'utils/model_sync_helper.dart';
import 'worker/setter.dart';
import 'worker/haptic.dart';
import 'worker/sender.dart';
import 'worker/desktop.dart';
import 'worker/theme.dart';
import 'worker/update.dart';
import 'worker/clients.dart';
import 'config/app_mode.dart';
import 'screens/mode_selection_screen.dart';
import 'services/internet/internet_chat_service.dart';

import 'package:shared_preferences/shared_preferences.dart';
// ignore: depend_on_referenced_packages
import 'package:flutter_chat_types/flutter_chat_types.dart' as types;
import 'package:flutter_chat_ui/flutter_chat_ui.dart';
import 'package:uuid/uuid.dart';
import 'package:image_picker/image_picker.dart';
import 'package:visibility_detector/visibility_detector.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
// ignore: depend_on_referenced_packages
import 'package:markdown/markdown.dart' as md;
import 'package:bitsdojo_window/bitsdojo_window.dart';
import 'package:flutter_displaymode/flutter_displaymode.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:dynamic_color/dynamic_color.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:version/version.dart';
import 'package:pwa_install/pwa_install.dart' as pwa;
import 'package:universal_html/html.dart' as html;

// client configuration

// use host or not, if false dialog is shown
const bool useHost = false;
// host of AI server, must be accessible from the client, without trailing slash
// ! will always be accepted as valid, even if [useHost] is false
const String fixedHost = "http://example.com:11434";
// use model or not, if false selector is shown
const bool useModel = false;
// model name as string, must be valid AI model!
const String fixedModel = "gemma";
// recommended models, shown with a star in model selector
const List<String> recommendedModels = ["gemma", "llama3"];
// allow opening of settings
const bool allowSettings = true;
// allow multiple chats
const bool allowMultipleChats = true;

// client configuration end

SharedPreferences? prefs;

String? model;
String? host;

bool multimodal = false;

List<types.Message> messages = [];
String? chatUuid;
bool chatAllowed = true;
String hoveredChat = "";

GlobalKey<ChatState>? chatKey;
final user = types.User(id: const Uuid().v4());
final assistant = types.User(id: const Uuid().v4());

bool settingsOpen = false;
bool desktopTitleVisible = true;
bool logoVisible = true;
bool menuVisible = false;
bool sendable = false;
bool updateDetectedOnStart = false;
double sidebarIconSize = 1;

SpeechToText speech = SpeechToText();
FlutterTts voice = FlutterTts();
bool voiceSupported = false;

BuildContext? mainContext;
void Function(void Function())? setGlobalState;
void Function(void Function())? setMainAppState;

// 全局回调函数，用于重新加载知识库
void Function()? reloadKnowledgeBases;

// 知识库相关变量
bool useRAG = false;
String? selectedKnowledgeBase;
List<Map<String, dynamic>> knowledgeBases = [];
List<Map<String, dynamic>> syncedKnowledgeBases = []; // 同步的知识库

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 必须在 getInstance 之前设置前缀
  SharedPreferences.setPrefix("Baymin.");

  // 初始化 SharedPreferences
  prefs = await SharedPreferences.getInstance();

  pwa.PWAInstall().setup(installCallback: () {});

  try {
    HttpOverrides.global = BayminHttpOverrides();
  } catch (_) {}

  runApp(const App());

  if (desktopFeature()) {
    doWhenWindowReady(() {
      appWindow.minSize = const Size(600, 450);
      appWindow.size = const Size(1200, 650);
      appWindow.alignment = Alignment.center;
      if (prefs!.getBool("maximizeOnStart") ?? false) {
        appWindow.maximize();
      }
      appWindow.show();
    });
  }
}

class App extends StatefulWidget {
  const App({
    super.key,
  });

  @override
  State<App> createState() => _AppState();
}

class _AppState extends State<App> {
  @override
  void initState() {
    super.initState();

    void load() async {
      try {
        await FlutterDisplayMode.setHighRefreshRate();
      } catch (_) {}

      // prefs 已经在 main() 中初始化了
      if (prefs == null) {
        // 如果还是 null，尝试重新获取
        prefs = await SharedPreferences.getInstance();
      }

      setState(() {});

      try {
        if ((await Permission.bluetoothConnect.isGranted) &&
            (await Permission.microphone.isGranted)) {
          voiceSupported = await speech.initialize();
        } else {
          prefs!.setBool("voiceModeEnabled", false);
          voiceSupported = false;
        }
      } catch (_) {
        prefs!.setBool("voiceModeEnabled", false);
        voiceSupported = false;
      }
    }

    load();
  }

  @override
  void dispose() {
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return DynamicColorBuilder(
        builder: (ColorScheme? lightDynamic, ColorScheme? darkDynamic) {
      colorSchemeLight = lightDynamic;
      colorSchemeDark = darkDynamic;
      return StatefulBuilder(builder: (context, setState) {
        setMainAppState = setState;
        return MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            localeListResolutionCallback: (deviceLocales, supportedLocales) {
              if (deviceLocales != null) {
                for (final locale in deviceLocales) {
                  var newLocale = Locale(locale.languageCode);
                  if (supportedLocales.contains(newLocale)) {
                    return locale;
                  }
                }
              }
              return const Locale("en");
            },
            onGenerateTitle: (context) {
              return AppLocalizations.of(context)!.appTitle;
            },
            theme: themeLight(),
            darkTheme: themeDark(),
            themeMode: themeMode(),
            home: const MainApp());
      });
    });
  }
}

class MainApp extends StatefulWidget {
  const MainApp({super.key});

  @override
  State<MainApp> createState() => _MainAppState();
}

class _MainAppState extends State<MainApp> {
  int tipId = Random().nextInt(5);
  final DeviceDiscoveryService _deviceService = DeviceDiscoveryService();
  final SimpleDeviceBroadcastService _broadcastService =
      SimpleDeviceBroadcastService();
  double chatLogoSize = 1.0; // 聊天界面logo动画大小
  MCPService? _mcpService;

  List<Widget> sidebar(
      BuildContext context, void Function(void Function()) setState) {
    List<Widget> items = [];

    // 聊天历史列表
    List<String> chats = prefs?.getStringList("chats") ?? [];

    // 添加新聊天按钮
    items.add(
      ListTile(
        leading: Icon(Icons.add, size: IconSizes.sidebarIcon),
        title: const Text('New Chat'),
        onTap: () {
          if (!chatAllowed) return;
          setState(() {
            messages = [];
            chatUuid = null;
          });
          if (!desktopLayoutRequired(context) &&
              Navigator.of(context).canPop()) {
            Navigator.of(context).pop();
          }
        },
      ),
    );

    items.add(const Divider());

    // 聊天历史
    for (String chatStr in chats) {
      try {
        final chat = jsonDecode(chatStr);
        final uuid = chat['uuid'];
        final title = chat['title'] ?? 'Untitled';
        final isActive = uuid == chatUuid;

        items.add(
          ListTile(
            leading: Icon(
              Icons.chat_bubble_outline,
              color: isActive ? Theme.of(context).colorScheme.primary : null,
              size: IconSizes.sidebarIcon,
            ),
            title: Text(
              title,
              style: TextStyle(
                fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
              ),
            ),
            selected: isActive,
            onTap: () {
              if (!chatAllowed) return;
              loadChat(uuid, setState);
              if (!desktopLayoutRequired(context) &&
                  Navigator.of(context).canPop()) {
                Navigator.of(context).pop();
              }
            },
            trailing: IconButton(
              icon: Icon(Icons.delete_outline, size: IconSizes.popupMenuItem),
              onPressed: () async {
                await deleteChatDialog(context, setState,
                    uuid: uuid, popSidebar: true);
              },
            ),
          ),
        );
      } catch (e) {
        print('Error parsing chat: $e');
      }
    }

    // 设置按钮 - 移除 Spacer，因为 ListView 不支持
    if (allowSettings) {
      // 如果聊天列表为空或很少，添加一些空间
      if (chats.length < 5) {
        items.add(const SizedBox(height: 20));
      }

      items.add(const Divider());

      // 调试信息 - 在所有平台显示
      items.add(
        ListTile(
          leading: Icon(Icons.bug_report, size: IconSizes.sidebarIcon),
          title: const Text('Debug Info'),
          subtitle: Text(
            'Mode: ${AppConfig.serverMode}',
            style: const TextStyle(fontSize: 12),
          ),
          onTap: () {
            showDialog(
              context: context,
              builder: (context) => AlertDialog(
                title: Text('Debug Info'),
                content: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('Server Mode: ${AppConfig.serverMode}'),
                      Text('Server URL: ${AppConfig.multiAgentServer}'),
                      Text('API Base: ${AppConfig.apiBaseUrl}'),
                      Text('Chat Endpoint: ${AppConfig.chatEndpoint}'),
                      Text('Models Endpoint: ${AppConfig.modelsEndpoint}'),
                      SizedBox(height: 10),
                      Text('Current Model: ${model ?? "None"}'),
                      Text('Host (old): ${host ?? "None"}'),
                      Text('Chat Allowed: $chatAllowed'),
                      SizedBox(height: 10),
                      Text('Saved Preferences:'),
                      Text(
                          '- serverMode: ${prefs?.getString('serverMode') ?? "Not set"}'),
                      Text(
                          '- multiAgentServer: ${prefs?.getString('multiAgentServer') ?? "Not set"}'),
                      Text('- host: ${prefs?.getString('host') ?? "Not set"}'),
                      SizedBox(height: 10),
                      Text(
                          'MCP Service: ${_mcpService != null ? "Initialized" : "Not initialized"}'),
                      Text(
                          'Screen Width: ${MediaQuery.of(context).size.width}'),
                      Text('Desktop Layout: ${desktopLayoutRequired(context)}'),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () async {
                      // 测试连接
                      try {
                        final connected =
                            await MultiAgentService().testConnection();
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                              content: Text(
                                  'Connection: ${connected ? "OK" : "Failed"}')),
                        );
                      } catch (e) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Error: $e')),
                        );
                      }
                    },
                    child: Text('Test Connection'),
                  ),
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: Text('Close'),
                  ),
                ],
              ),
            );
          },
        ),
      );

      // 多Agent模式下的功能
      if (AppModeManager.isMultiAgentMode) {
        // 知识库管理
        items.add(
          ListTile(
            leading: Icon(
              useRAG ? Icons.folder : Icons.folder_outlined,
              color: useRAG ? Theme.of(context).colorScheme.primary : null,
              size: IconSizes.sidebarIcon,
            ),
            title: const Text('Knowledge Base'),
            subtitle: useRAG && selectedKnowledgeBase != null
                ? Text(
                    'Using: ${_getKnowledgeBaseName(selectedKnowledgeBase)}',
                    style: const TextStyle(fontSize: 12),
                  )
                : null,
            onTap: () {
              _showKnowledgeBaseSelector();
              if (!desktopLayoutRequired(context) &&
                  Navigator.of(context).canPop()) {
                Navigator.of(context).pop();
              }
            },
          ),
        );

        // MCP服务
        items.add(
          ListTile(
            leading: Icon(
              Icons.extension,
              size: IconSizes.sidebarIcon,
            ),
            title: const Text('MCP Services'),
            onTap: () {
              if (_mcpService != null) {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) =>
                        ChangeNotifierProvider<MCPService>.value(
                      value: _mcpService!,
                      child: const MCPServiceListScreen(),
                    ),
                  ),
                );
                if (!desktopLayoutRequired(context) &&
                    Navigator.of(context).canPop()) {
                  Navigator.of(context).pop();
                }
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('MCP服务未初始化')),
                );
              }
            },
          ),
        );

        // 同步管理
        items.add(
          ListTile(
            leading: Icon(
              Icons.sync,
              size: IconSizes.sidebarIcon,
            ),
            title: const Text('Sync Manager'),
            subtitle: const Text('Manage device sync',
                style: TextStyle(fontSize: 12)),
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => const KnowledgeSyncScreen(),
                ),
              );
              if (!desktopLayoutRequired(context) &&
                  Navigator.of(context).canPop()) {
                Navigator.of(context).pop();
              }
            },
          ),
        );

        items.add(const Divider());
      }

      // 模式选择按钮
      items.add(
        ListTile(
          leading: Icon(Icons.swap_horiz, size: IconSizes.sidebarIcon),
          title: const Text('Mode Selection'),
          subtitle: Text(
            'Current: ${AppModeManager.getModeName()}',
            style: const TextStyle(fontSize: 12),
          ),
          onTap: () {
            Navigator.of(context)
                .push(
              MaterialPageRoute(
                builder: (context) => const ModeSelectionScreen(),
              ),
            )
                .then((_) {
              // 返回后刷新状态
              setState(() {
                // 同步模型选择
                ModelSyncHelper.syncModelSelection();
              });
              if (AppModeManager.isMultiAgentMode) {
                _loadKnowledgeBases();
              }
            });
          },
        ),
      );

      items.add(
        ListTile(
          leading: Icon(Icons.settings, size: IconSizes.sidebarIcon),
          title: const Text('Settings'),
          onTap: () {
            setGlobalState = setState;
            settingsOpen = true;
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (context) => const ScreenSettings(),
              ),
            );
          },
        ),
      );

      // 移除了同步管理入口，只在知识库管理界面中保留
    }

    return items;
  }

  @override
  void initState() {
    super.initState();
    mainContext = context;

    // 设置全局回调
    reloadKnowledgeBases = _loadKnowledgeBases;

    if (kIsWeb) {
      html.querySelector(".loader")?.remove();
    }

    WidgetsBinding.instance.addPostFrameCallback(
      (_) async {
        // 等待 prefs 初始化
        if (prefs == null) {
          await Future.doWhile(
              () => Future.delayed(const Duration(milliseconds: 1)).then((_) {
                    return prefs == null;
                  }));
        }

        if (!(allowSettings || useHost)) {
          showDialog(
              // ignore: use_build_context_synchronously
              context: context,
              builder: (context) {
                // ignore: prefer_const_constructors
                return PopScope(
                    canPop: false,
                    // ignore: prefer_const_constructors
                    child: Dialog.fullscreen(
                        backgroundColor: Colors.black,
                        // ignore: prefer_const_constructors
                        child: Padding(
                            padding: const EdgeInsets.all(16),
                            // ignore: prefer_const_constructors
                            child: Text(
                                "*Build Error:*\n\nuseHost: $useHost\nallowSettings: $allowSettings\n\nYou created this build? One of them must be set to true or the app is not functional!\n\nYou received this build by someone else? Please contact them and report the issue.",
                                style: const TextStyle(
                                    color: Colors.red,
                                    fontFamily: "monospace")))));
              });
        }

        // 直接设置为已完成，跳过欢迎界面
        await prefs!.setBool("welcomeFinished", true);

        /*
        // prefs!.remove("welcomeFinished");
        if (!(prefs!.getBool("welcomeFinished") ?? false) && allowSettings) {
          // ignore: use_build_context_synchronously
          Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (context) => const ScreenWelcome()));
          return;
        }
        */

        if (!allowMultipleChats &&
            (prefs!.getStringList("chats") ?? []).isNotEmpty) {
          chatUuid =
              jsonDecode((prefs!.getStringList("chats") ?? [])[0])["uuid"];
          loadChat(chatUuid!, setState);
        }

        // 加载应用模式
        final savedMode = prefs!.getString('app_mode') ?? 'local';
        AppModeManager.currentMode =
            savedMode == 'internet' ? AppMode.internet : AppMode.local;

        // 加载本地子模式
        final savedSubMode = prefs!.getString('local_sub_mode') ?? 'multiAgent';
        AppModeManager.localSubMode = savedSubMode == 'ollama'
            ? LocalSubMode.ollama
            : LocalSubMode.multiAgent;

        // 为了兼容旧版本，同步更新AppConfig
        AppConfig.serverMode =
            AppModeManager.localSubMode == LocalSubMode.ollama
                ? 'ollama'
                : 'multiagent';

        // 加载保存的服务器地址，如果没有则使用默认值
        String savedServer = prefs!.getString('multiAgentServer') ?? '';
        if (savedServer.isNotEmpty) {
          AppConfig.multiAgentServer = savedServer;
        }
        // 如果是Android且没有保存的地址，AppConfig会自动使用Android配置

        // 如果是从旧版本升级，清理旧的Ollama配置
        if (AppModeManager.isMultiAgentMode && prefs!.containsKey('host')) {
          await prefs!.remove('host');
        }

        print('Current app mode: ${AppModeManager.getModeName()}');
        print('Multi-agent server: ${AppConfig.multiAgentServer}');

        // 设置模型和主机信息
        setState(() {
          // 如果是固定模型模式且不是Internet模式
          if (useModel && !AppModeManager.isInternetMode) {
            model = fixedModel;
            chatAllowed = true;
          } else {
            // 使用同步帮助类加载模型
            ModelSyncHelper.syncModelSelection();
          }
          host = useHost ? fixedHost : prefs?.getString("host");
        });

        // 如果是多Agent模式，加载知识库和初始化MCP服务
        if (AppModeManager.isMultiAgentMode) {
          print('Loading knowledge bases...');
          _loadKnowledgeBases();

          // 加载保存的RAG设置
          useRAG = prefs!.getBool('useRAG') ?? false;
          selectedKnowledgeBase = prefs!.getString('selectedKnowledgeBase');
          print('RAG enabled: $useRAG, Selected KB: $selectedKnowledgeBase');

          // 测试同步API
          print('Testing sync API...');
          MultiAgentService().getSyncedKnowledgeBases().then((synced) {
            print('Synced KBs loaded: ${synced.length}');
          }).catchError((e) {
            print('Error loading synced KBs: $e');
          });

          // 初始化MCP服务
          print(
              'Initializing MCP service with URL: ${AppConfig.multiAgentServer}');
          try {
            _mcpService = MCPService(
              baseUrl: AppConfig.multiAgentServer,
              deviceIdService: DeviceIdService(),
            );
            print('MCP service initialized successfully');
          } catch (e) {
            print('Failed to initialize MCP service: $e');
          }

          // 初始化设备发现服务
          _deviceService.initialize();
          // 启动设备广播服务
          _broadcastService.start().then((_) {
            print('Device broadcast service started');
          }).catchError((e) {
            print('Failed to start device broadcast service: $e');
          });
        }

        if (host == null && AppModeManager.isOllamaMode) {
          // ignore: use_build_context_synchronously
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
              // ignore: use_build_context_synchronously
              content: Text(AppLocalizations.of(context)!.noHostSelected),
              showCloseIcon: true));
        }

        // 确保 UI更新以显示知识库图标
        setState(() {});

        if (prefs!.getBool("checkUpdateOnSettingsOpen") ?? true) {
          updateDetectedOnStart = await checkUpdate(setState);
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    // 添加调试日志
    print('[MainApp] Building with:');
    print('  - App Mode: ${AppModeManager.getModeName()}');
    print('  - Model: $model');
    print('  - Chat Allowed: $chatAllowed');
    print('  - Messages count: ${messages.length}');
    print('  - Prefs initialized: ${prefs != null}');
    print('  - Desktop feature: ${desktopFeature()}');
    print(
        '  - Platform: ${kIsWeb ? "Web" : (Platform.isAndroid ? "Android" : (Platform.isIOS ? "iOS" : "Desktop"))}');

    // 如果prefs还没有初始化，显示加载器
    if (prefs == null) {
      return Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    // 获取Internet模型的显示名称
    String _getInternetModelDisplayName(String modelId) {
      final models = InternetChatService.getAvailableModels();
      final model = models.firstWhere(
        (m) => m['id'] == modelId,
        orElse: () => {'name': modelId},
      );
      return model['name'] ?? modelId;
    }

    Widget selector = InkWell(
        onTap: !useModel
            ? () {
                // Internet模式下也可以选择模型
                if (host == null && AppModeManager.isOllamaMode) {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                      content:
                          Text(AppLocalizations.of(context)!.noHostSelected),
                      showCloseIcon: true));
                  return;
                }
                setModel(context, setState);
              }
            : null,
        splashFactory: NoSplash.splashFactory,
        highlightColor: Colors.transparent,
        enableFeedback: false,
        hoverColor: Colors.transparent,
        child: SizedBox(
            height: 200,
            child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Internet模式显示图标
                  if (AppModeManager.isInternetMode)
                    const Padding(
                      padding: EdgeInsets.only(right: 8),
                      child: Icon(Icons.language, size: 20),
                    ),
                  Flexible(
                      child: Text(
                          AppModeManager.isInternetMode && model != null
                              ? _getInternetModelDisplayName(model!)
                              : (model ??
                                      AppLocalizations.of(context)!
                                          .noSelectedModel)
                                  .split(":")[0],
                          overflow: TextOverflow.fade,
                          style: const TextStyle(
                              fontFamily: "monospace", fontSize: 16))),
                  useModel
                      ? const SizedBox.shrink()
                      : const Icon(Icons.expand_more_rounded)
                ])));

    // 如果出现错误，显示错误信息
    try {
      return WindowBorder(
        color: Theme.of(context).colorScheme.surface,
        child: Scaffold(
            appBar: AppBar(
                titleSpacing: 0,
                title: Row(
                    children: desktopFeature()
                        ? desktopLayoutRequired(context)
                            ? [
                                SizedBox(
                                    width: 304,
                                    height: 200,
                                    child: MoveWindow()),
                                SizedBox(
                                    height: 200,
                                    child: AnimatedOpacity(
                                        opacity: menuVisible ? 1.0 : 0.0,
                                        duration:
                                            const Duration(milliseconds: 300),
                                        child: VerticalDivider(
                                            width: 2,
                                            color: Theme.of(context)
                                                .colorScheme
                                                .onSurface
                                                .withAlpha(20)))),
                                AnimatedOpacity(
                                  opacity: desktopTitleVisible ? 1.0 : 0.0,
                                  duration: desktopTitleVisible
                                      ? const Duration(milliseconds: 300)
                                      : const Duration(milliseconds: 0),
                                  child: Padding(
                                    padding: const EdgeInsets.all(16),
                                    child: selector,
                                  ),
                                ),
                                Expanded(
                                    child: SizedBox(
                                        height: 200, child: MoveWindow()))
                              ]
                            : [
                                SizedBox(
                                    width: 90,
                                    height: 200,
                                    child: MoveWindow()),
                                Expanded(
                                    child: SizedBox(
                                        height: 200, child: MoveWindow())),
                                selector,
                                Expanded(
                                    child: SizedBox(
                                        height: 200, child: MoveWindow()))
                              ]
                        : desktopLayoutRequired(context)
                            ? [
                                // bottom left tile
                                const SizedBox(width: 304, height: 200),
                                SizedBox(
                                    height: 200,
                                    child: AnimatedOpacity(
                                        opacity: menuVisible ? 1.0 : 0.0,
                                        duration:
                                            const Duration(milliseconds: 300),
                                        child: VerticalDivider(
                                            width: 2,
                                            color: Theme.of(context)
                                                .colorScheme
                                                .onSurface
                                                .withAlpha(20)))),
                                AnimatedOpacity(
                                  opacity: desktopTitleVisible ? 1.0 : 0.0,
                                  duration: desktopTitleVisible
                                      ? const Duration(milliseconds: 300)
                                      : const Duration(milliseconds: 0),
                                  child: Padding(
                                    padding: const EdgeInsets.all(16),
                                    child: selector,
                                  ),
                                ),
                                const Expanded(child: SizedBox(height: 200))
                              ]
                            : [Expanded(child: selector)]),
                actions: [
                  const SizedBox(width: 4),
                  // 调试信息按钮 - 仅在桌面端显示
                  if (desktopLayoutRequired(context))
                    IconButton(
                      icon: Icon(Icons.info_outline,
                          size: IconSizes.appBarAction),
                      onPressed: () {
                        showDialog(
                          context: context,
                          builder: (context) => AlertDialog(
                            title: Text('Debug Info'),
                            content: SingleChildScrollView(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text('Server Mode: ${AppConfig.serverMode}'),
                                  Text(
                                      'Server URL: ${AppConfig.multiAgentServer}'),
                                  Text('API Base: ${AppConfig.apiBaseUrl}'),
                                  Text(
                                      'Chat Endpoint: ${AppConfig.chatEndpoint}'),
                                  Text(
                                      'Models Endpoint: ${AppConfig.modelsEndpoint}'),
                                  SizedBox(height: 10),
                                  Text('Current Model: ${model ?? "None"}'),
                                  Text('Host (old): ${host ?? "None"}'),
                                  Text('Chat Allowed: $chatAllowed'),
                                  SizedBox(height: 10),
                                  Text('Saved Preferences:'),
                                  Text(
                                      '- serverMode: ${prefs?.getString('serverMode') ?? "Not set"}'),
                                  Text(
                                      '- multiAgentServer: ${prefs?.getString('multiAgentServer') ?? "Not set"}'),
                                  Text(
                                      '- host: ${prefs?.getString('host') ?? "Not set"}'),
                                ],
                              ),
                            ),
                            actions: [
                              TextButton(
                                onPressed: () async {
                                  // 测试连接
                                  try {
                                    final connected = await MultiAgentService()
                                        .testConnection();
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                          content: Text(
                                              'Connection: ${connected ? "OK" : "Failed"}')),
                                    );
                                  } catch (e) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('Error: $e')),
                                    );
                                  }
                                },
                                child: Text('Test Connection'),
                              ),
                              TextButton(
                                onPressed: () {
                                  Navigator.pop(context);
                                  // 打开同步管理界面
                                  Navigator.of(context).push(
                                    MaterialPageRoute(
                                      builder: (context) =>
                                          const KnowledgeSyncScreen(),
                                    ),
                                  );
                                },
                                child: Text('Open Sync Manager'),
                              ),
                              TextButton(
                                onPressed: () => Navigator.pop(context),
                                child: Text('Close'),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  // 知识库按钮 - 在移动端和桌面端都显示
                  if (AppModeManager.isMultiAgentMode)
                    Tooltip(
                      message: useRAG && selectedKnowledgeBase != null
                          ? 'Using: ${knowledgeBases.firstWhere((kb) => kb['id'] == selectedKnowledgeBase, orElse: () => {
                                'name': 'Unknown'
                              })['name']}'
                          : 'Knowledge Base',
                      child: IconButton(
                        icon: Icon(
                          useRAG ? Icons.folder : Icons.folder_outlined,
                          color: useRAG
                              ? Theme.of(context).colorScheme.primary
                              : null,
                          size: IconSizes.appBarAction,
                        ),
                        onPressed: () {
                          _showKnowledgeBaseSelector();
                        },
                      ),
                    ),
                  // MCP服务按钮 - 在移动端和桌面端都显示
                  if (AppModeManager.isMultiAgentMode)
                    IconButton(
                      icon: Icon(
                        Icons.extension,
                        size: IconSizes.appBarAction,
                      ),
                      onPressed: () async {
                        // 如果MCP服务未初始化，尝试初始化
                        if (_mcpService == null) {
                          print(
                              'MCP Service not initialized, trying to initialize...');
                          print(
                              'Current server URL: ${AppConfig.multiAgentServer}');

                          // 显示加载指示器
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Row(
                                children: [
                                  SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(
                                          Colors.white),
                                    ),
                                  ),
                                  SizedBox(width: 16),
                                  Text('Initializing MCP service...'),
                                ],
                              ),
                              duration: Duration(seconds: 1),
                            ),
                          );

                          try {
                            // 先测试服务器连接
                            final connected =
                                await MultiAgentService().testConnection();
                            if (!connected) {
                              throw Exception('Server connection failed');
                            }

                            setState(() {
                              _mcpService = MCPService(
                                baseUrl: AppConfig.multiAgentServer,
                                deviceIdService: DeviceIdService(),
                              );
                            });
                            print('MCP Service initialized successfully');
                          } catch (e) {
                            print('Failed to initialize MCP service: $e');

                            // 显示详细错误信息
                            if (context.mounted) {
                              showDialog(
                                context: context,
                                builder: (context) => AlertDialog(
                                  title: const Text('MCP Service Error'),
                                  content: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text('Failed to initialize MCP service.'),
                                      const SizedBox(height: 16),
                                      Text(
                                          'Server URL: ${AppConfig.multiAgentServer}'),
                                      const SizedBox(height: 8),
                                      Text('Error: ${e.toString()}'),
                                      const SizedBox(height: 16),
                                      const Text('Please check:',
                                          style: TextStyle(
                                              fontWeight: FontWeight.bold)),
                                      const Text('1. Server is running'),
                                      const Text(
                                          '2. Correct server IP address'),
                                      const Text(
                                          '3. Phone and PC on same WiFi'),
                                      const Text(
                                          '4. Firewall allows port 8000'),
                                    ],
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () {
                                        Navigator.pop(context);
                                        // 打开设置
                                        setGlobalState = setState;
                                        settingsOpen = true;
                                        Navigator.of(context).push(
                                          MaterialPageRoute(
                                            builder: (context) =>
                                                const ScreenSettings(),
                                          ),
                                        );
                                      },
                                      child: const Text('Open Settings'),
                                    ),
                                    TextButton(
                                      onPressed: () => Navigator.pop(context),
                                      child: const Text('OK'),
                                    ),
                                  ],
                                ),
                              );
                            }
                            return;
                          }
                        }

                        if (_mcpService != null) {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (context) =>
                                  ChangeNotifierProvider<MCPService>.value(
                                value: _mcpService!,
                                child: const MCPServiceListScreen(),
                              ),
                            ),
                          );
                        }
                      },
                      tooltip: 'MCP Services',
                    ),
                  ...?desktopControlsActions(context, [])
                ],
                bottom: PreferredSize(
                    preferredSize: const Size.fromHeight(1),
                    child: (!chatAllowed && model != null)
                        ? const LinearProgressIndicator()
                        : desktopLayout(context)
                            ? AnimatedOpacity(
                                opacity: menuVisible ? 1.0 : 0.0,
                                duration: const Duration(milliseconds: 300),
                                child: Divider(
                                    height: 2,
                                    color: Theme.of(context)
                                        .colorScheme
                                        .onSurface
                                        .withAlpha(20)))
                            : const SizedBox.shrink()),
                automaticallyImplyLeading: !desktopLayoutRequired(context)),
            body: Row(
              children: [
                desktopLayoutRequired(context)
                    ? SizedBox(
                        width: 304,
                        height: double.infinity,
                        child: VisibilityDetector(
                            key: const Key("menuVisible"),
                            onVisibilityChanged: (VisibilityInfo info) {
                              if (settingsOpen) return;
                              menuVisible = info.visibleFraction > 0;
                              try {
                                setState(() {});
                              } catch (_) {}
                            },
                            child: AnimatedOpacity(
                                opacity: menuVisible ? 1.0 : 0.0,
                                duration: const Duration(milliseconds: 300),
                                child: ListView(
                                    children: sidebar(context, setState)))))
                    : const SizedBox.shrink(),
                desktopLayout(context)
                    ? AnimatedOpacity(
                        opacity: menuVisible ? 1.0 : 0.0,
                        duration: const Duration(milliseconds: 300),
                        child: VerticalDivider(
                            width: 2,
                            color: Theme.of(context)
                                .colorScheme
                                .onSurface
                                .withAlpha(20)))
                    : const SizedBox.shrink(),
                Expanded(
                  child: Center(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      mainAxisSize: MainAxisSize.max,
                      children: [
                        // RAG 状态指示器
                        if (AppModeManager.isMultiAgentMode &&
                            useRAG &&
                            selectedKnowledgeBase != null)
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 8),
                            child: Material(
                              color: Theme.of(context)
                                  .colorScheme
                                  .primaryContainer,
                              borderRadius: BorderRadius.circular(20),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(20),
                                onTap: _showKnowledgeBaseSelector,
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 16, vertical: 8),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        Icons.auto_stories,
                                        size: 16,
                                        color: Theme.of(context)
                                            .colorScheme
                                            .onPrimaryContainer,
                                      ),
                                      const SizedBox(width: 8),
                                      Text(
                                        'Using: ${_getKnowledgeBaseName(selectedKnowledgeBase)}',
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: Theme.of(context)
                                              .colorScheme
                                              .onPrimaryContainer,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Icon(
                                        Icons.close,
                                        size: 16,
                                        color: Theme.of(context)
                                            .colorScheme
                                            .onPrimaryContainer,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        Flexible(
                          child: Container(
                            constraints: const BoxConstraints(maxWidth: 1000),
                            child: Chat(
                                messages: messages,
                                key: chatKey,
                                textMessageBuilder: (p0,
                                    {required messageWidth,
                                    required showName}) {
                                  var white =
                                      const TextStyle(color: Colors.white);
                                  bool greyed = false;
                                  String text = p0.text;
                                  if (text.trim() == "") {
                                    text =
                                        "_Empty AI response, try restarting conversation_";
                                    greyed = true;
                                  }
                                  return Padding(
                                      padding: const EdgeInsets.only(
                                          left: 20,
                                          right: 23,
                                          top: 17,
                                          bottom: 17),
                                      child: Theme(
                                        data: Theme.of(context).copyWith(
                                            scrollbarTheme:
                                                const ScrollbarThemeData(
                                                    thumbColor:
                                                        WidgetStatePropertyAll(
                                                            Colors.grey))),
                                        child: MarkdownBody(
                                            data: text,
                                            onTapLink: (text, href, title) async {
                                              selectionHaptic();
                                              try {
                                                var url = Uri.parse(href!);
                                                if (await canLaunchUrl(url)) {
                                                  launchUrl(
                                                      mode: LaunchMode
                                                          .inAppBrowserView,
                                                      url);
                                                } else {
                                                  throw Exception();
                                                }
                                              } catch (_) {
                                                // ignore: use_build_context_synchronously
                                                ScaffoldMessenger.of(context)
                                                    .showSnackBar(SnackBar(
                                                        content: Text(
                                                            AppLocalizations.of(
                                                                    // ignore: use_build_context_synchronously
                                                                    context)!
                                                                .settingsHostInvalid(
                                                                    "url")),
                                                        showCloseIcon: true));
                                              }
                                            },
                                            extensionSet: md.ExtensionSet(
                                              md.ExtensionSet.gitHubFlavored
                                                  .blockSyntaxes,
                                              <md.InlineSyntax>[
                                                md.EmojiSyntax(),
                                                ...md
                                                    .ExtensionSet
                                                    .gitHubFlavored
                                                    .inlineSyntaxes
                                              ],
                                            ),
                                            imageBuilder: (uri, title, alt) {
                                              Widget errorImage = InkWell(
                                                  onTap: () {
                                                    selectionHaptic();
                                                    ScaffoldMessenger.of(
                                                            context)
                                                        .showSnackBar(SnackBar(
                                                            content: Text(
                                                                AppLocalizations.of(
                                                                        context)!
                                                                    .notAValidImage),
                                                            showCloseIcon:
                                                                true));
                                                  },
                                                  child: Container(
                                                      decoration: BoxDecoration(
                                                          borderRadius:
                                                              BorderRadius
                                                                  .circular(8),
                                                          color: Theme.of(context)
                                                                      .brightness ==
                                                                  Brightness
                                                                      .light
                                                              ? Colors.white
                                                              : Colors.black),
                                                      padding:
                                                          const EdgeInsets.only(
                                                              left: 100,
                                                              right: 100,
                                                              top: 32),
                                                      child: const Image(
                                                          image: AssetImage(
                                                              "assets/logo512error.png"))));
                                              if (uri.isAbsolute) {
                                                return Image.network(
                                                    uri.toString(),
                                                    errorBuilder: (context,
                                                        error, stackTrace) {
                                                  return errorImage;
                                                });
                                              } else {
                                                return errorImage;
                                              }
                                            },
                                            styleSheet: (p0.author == user)
                                                ? MarkdownStyleSheet(
                                                    p: const TextStyle(
                                                        color: Colors.white,
                                                        fontSize: 16,
                                                        fontWeight:
                                                            FontWeight.w500),
                                                    blockquoteDecoration:
                                                        BoxDecoration(
                                                      color: Colors.grey[800],
                                                      borderRadius:
                                                          BorderRadius.circular(
                                                              8),
                                                    ),
                                                    code: const TextStyle(
                                                        color: Colors.black,
                                                        backgroundColor:
                                                            Colors.white),
                                                    codeblockDecoration:
                                                        BoxDecoration(
                                                            color: Colors.white,
                                                            borderRadius:
                                                                BorderRadius.circular(
                                                                    8)),
                                                    h1: white,
                                                    h2: white,
                                                    h3: white,
                                                    h4: white,
                                                    h5: white,
                                                    h6: white,
                                                    listBullet: white,
                                                    horizontalRuleDecoration: BoxDecoration(
                                                        border: Border(
                                                            top: BorderSide(
                                                                color: Colors
                                                                    .grey[800]!,
                                                                width: 1))),
                                                    tableBorder: TableBorder.all(
                                                        color: Colors.white),
                                                    tableBody: white)
                                                : (Theme.of(context).brightness ==
                                                        Brightness.light)
                                                    ? MarkdownStyleSheet(
                                                        p: TextStyle(
                                                            color: greyed ? Colors.grey : Colors.black,
                                                            fontSize: 16,
                                                            fontWeight: FontWeight.w500),
                                                        blockquoteDecoration: BoxDecoration(
                                                          color:
                                                              Colors.grey[200],
                                                          borderRadius:
                                                              BorderRadius
                                                                  .circular(8),
                                                        ),
                                                        code: const TextStyle(color: Colors.white, backgroundColor: Colors.black),
                                                        codeblockDecoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(8)),
                                                        horizontalRuleDecoration: BoxDecoration(border: Border(top: BorderSide(color: Colors.grey[200]!, width: 1))))
                                                    : MarkdownStyleSheet(
                                                        p: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w500),
                                                        blockquoteDecoration: BoxDecoration(
                                                          color:
                                                              Colors.grey[800]!,
                                                          borderRadius:
                                                              BorderRadius
                                                                  .circular(8),
                                                        ),
                                                        code: const TextStyle(color: Colors.black, backgroundColor: Colors.white),
                                                        codeblockDecoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(8)),
                                                        horizontalRuleDecoration: BoxDecoration(border: Border(top: BorderSide(color: Colors.grey[200]!, width: 1))))),
                                      ));
                                },
                                imageMessageBuilder: (p0,
                                    {required messageWidth}) {
                                  return SizedBox(
                                      width: desktopLayout(context)
                                          ? 360.0
                                          : 160.0,
                                      child: MarkdownBody(
                                          data: "![${p0.name}](${p0.uri})"));
                                },
                                disableImageGallery: true,
                                emptyState: Center(
                                    child: VisibilityDetector(
                                        key: const Key("logoVisible"),
                                        onVisibilityChanged:
                                            (VisibilityInfo info) {
                                          if (settingsOpen) return;
                                          logoVisible =
                                              info.visibleFraction > 0;
                                          try {
                                            setState(() {});
                                          } catch (_) {}
                                        },
                                        child: AnimatedOpacity(
                                            opacity: logoVisible ? 1.0 : 0.0,
                                            duration: const Duration(
                                                milliseconds: 500),
                                            child: InkWell(
                                              splashFactory:
                                                  NoSplash.splashFactory,
                                              highlightColor:
                                                  Colors.transparent,
                                              enableFeedback: false,
                                              hoverColor: Colors.transparent,
                                              onTap: () async {
                                                if (chatLogoSize != 1) return;
                                                heavyHaptic();
                                                setState(() {
                                                  chatLogoSize = LogoAnimationConfig
                                                      .dramaticScaleMin; // 使用更夸张的缩放
                                                });
                                                await Future.delayed(
                                                    const Duration(
                                                        milliseconds:
                                                            LogoAnimationConfig
                                                                .shrinkDuration));
                                                setState(() {
                                                  chatLogoSize =
                                                      LogoAnimationConfig
                                                          .dramaticScaleMax;
                                                });
                                                await Future.delayed(
                                                    const Duration(
                                                        milliseconds:
                                                            LogoAnimationConfig
                                                                .expandDuration));
                                                setState(() {
                                                  chatLogoSize = 1.0;
                                                });
                                              },
                                              child: AnimatedScale(
                                                scale: chatLogoSize,
                                                duration: const Duration(
                                                    milliseconds:
                                                        LogoAnimationConfig
                                                            .scaleDuration),
                                                child: Image.asset(
                                                    "assets/logo512.png",
                                                    width: IconSizes.chatLogo,
                                                    height: IconSizes.chatLogo),
                                              ),
                                            )))),
                                onSendPressed: (p0) {
                                  send(p0.text, context, setState);
                                },
                                onMessageDoubleTap: (context, p1) {
                                  selectionHaptic();
                                  if (!chatAllowed) return;
                                  if (p1.author == assistant) return;
                                  for (var i = 0; i < messages.length; i++) {
                                    if (messages[i].id == p1.id) {
                                      List messageList =
                                          (jsonDecode(jsonEncode(messages))
                                                  as List)
                                              .reversed
                                              .toList();
                                      bool found = false;
                                      List index = [];
                                      for (var j = 0;
                                          j < messageList.length;
                                          j++) {
                                        if (messageList[j]["id"] == p1.id) {
                                          found = true;
                                        }
                                        if (found) {
                                          index.add(messageList[j]["id"]);
                                        }
                                      }
                                      for (var j = 0; j < index.length; j++) {
                                        for (var k = 0;
                                            k < messages.length;
                                            k++) {
                                          if (messages[k].id == index[j]) {
                                            messages.removeAt(k);
                                          }
                                        }
                                      }
                                      break;
                                    }
                                  }
                                  saveChat(chatUuid!, setState);
                                  setState(() {});
                                },
                                onMessageLongPress: (context, p1) async {
                                  selectionHaptic();

                                  if (!(prefs!.getBool("enableEditing") ??
                                      true)) {
                                    return;
                                  }

                                  var index = -1;
                                  if (!chatAllowed) return;
                                  for (var i = 0; i < messages.length; i++) {
                                    if (messages[i].id == p1.id) {
                                      index = i;
                                      break;
                                    }
                                  }

                                  var text =
                                      (messages[index] as types.TextMessage)
                                          .text;
                                  var input = await prompt(
                                    context,
                                    title: AppLocalizations.of(context)!
                                        .dialogEditMessageTitle,
                                    value: text,
                                    keyboard: TextInputType.multiline,
                                    maxLines: (text.length >= 100)
                                        ? 10
                                        : ((text.length >= 50) ? 5 : 3),
                                  );
                                  if (input == "") return;

                                  messages[index] = types.TextMessage(
                                    author: p1.author,
                                    createdAt: p1.createdAt,
                                    id: p1.id,
                                    text: input,
                                  );
                                  setState(() {});
                                },
                                onAttachmentPressed:
                                    (!multimodal ||
                                            AppModeManager.isInternetMode)
                                        ? (prefs?.getBool("voiceModeEnabled") ??
                                                false)
                                            ? (model != null)
                                                ? () {
                                                    selectionHaptic();
                                                    setGlobalState = setState;
                                                    settingsOpen = true;
                                                    logoVisible = false;
                                                    Navigator.of(context).push(
                                                        MaterialPageRoute(
                                                            builder: (context) =>
                                                                const ScreenVoice()));
                                                  }
                                                : null
                                            : null
                                        : () {
                                            selectionHaptic();
                                            if (!chatAllowed || model == null) {
                                              return;
                                            }
                                            if (desktopFeature()) {
                                              FilePicker.platform
                                                  .pickFiles(
                                                      type: FileType.image)
                                                  .then((value) async {
                                                if (value == null) return;
                                                if (!multimodal) return;

                                                var encoded = base64.encode(
                                                    await File(value
                                                            .files.first.path!)
                                                        .readAsBytes());
                                                messages.insert(
                                                    0,
                                                    types.ImageMessage(
                                                        author: user,
                                                        id: const Uuid().v4(),
                                                        name: value
                                                            .files.first.name,
                                                        size: value
                                                            .files.first.size,
                                                        uri:
                                                            "data:image/png;base64,$encoded"));

                                                setState(() {});
                                              });

                                              return;
                                            }
                                            showModalBottomSheet(
                                                context: context,
                                                builder: (context) {
                                                  return Container(
                                                      width: double.infinity,
                                                      padding:
                                                          const EdgeInsets.only(
                                                              left: 16,
                                                              right: 16,
                                                              top: 16),
                                                      child: Column(
                                                          mainAxisSize:
                                                              MainAxisSize.min,
                                                          children: [
                                                            (prefs?.getBool(
                                                                        "voiceModeEnabled") ??
                                                                    false)
                                                                ? SizedBox(
                                                                    width: double
                                                                        .infinity,
                                                                    child: OutlinedButton
                                                                        .icon(
                                                                            onPressed:
                                                                                () async {
                                                                              selectionHaptic();
                                                                              Navigator.of(context).pop();
                                                                              setGlobalState = setState;
                                                                              settingsOpen = true;
                                                                              logoVisible = false;
                                                                              Navigator.of(context).push(MaterialPageRoute(builder: (context) => const ScreenVoice()));
                                                                            },
                                                                            icon: const Icon(Icons
                                                                                .headphones_rounded),
                                                                            label: Text(AppLocalizations.of(context)!
                                                                                .settingsTitleVoice)))
                                                                : const SizedBox
                                                                    .shrink(),
                                                            (prefs?.getBool(
                                                                        "voiceModeEnabled") ??
                                                                    false)
                                                                ? const SizedBox(
                                                                    height: 8)
                                                                : const SizedBox
                                                                    .shrink(),
                                                            SizedBox(
                                                                width: double
                                                                    .infinity,
                                                                child: OutlinedButton
                                                                    .icon(
                                                                        onPressed:
                                                                            () async {
                                                                          selectionHaptic();

                                                                          Navigator.of(context)
                                                                              .pop();
                                                                          final result =
                                                                              await ImagePicker().pickImage(
                                                                            source:
                                                                                ImageSource.camera,
                                                                          );
                                                                          if (result ==
                                                                              null) {
                                                                            return;
                                                                          }

                                                                          final bytes =
                                                                              await result.readAsBytes();
                                                                          final image =
                                                                              await decodeImageFromList(bytes);

                                                                          final message =
                                                                              types.ImageMessage(
                                                                            author:
                                                                                user,
                                                                            createdAt:
                                                                                DateTime.now().millisecondsSinceEpoch,
                                                                            height:
                                                                                image.height.toDouble(),
                                                                            id: const Uuid().v4(),
                                                                            name:
                                                                                result.name,
                                                                            size:
                                                                                bytes.length,
                                                                            uri:
                                                                                result.path,
                                                                            width:
                                                                                image.width.toDouble(),
                                                                          );

                                                                          messages.insert(
                                                                              0,
                                                                              message);
                                                                          setState(
                                                                              () {});
                                                                          selectionHaptic();
                                                                        },
                                                                        icon: const Icon(Icons
                                                                            .photo_camera_rounded),
                                                                        label: Text(
                                                                            AppLocalizations.of(context)!.takeImage))),
                                                            const SizedBox(
                                                                height: 8),
                                                            SizedBox(
                                                                width: double
                                                                    .infinity,
                                                                child: OutlinedButton
                                                                    .icon(
                                                                        onPressed:
                                                                            () async {
                                                                          selectionHaptic();

                                                                          Navigator.of(context)
                                                                              .pop();
                                                                          final result =
                                                                              await ImagePicker().pickImage(
                                                                            source:
                                                                                ImageSource.gallery,
                                                                          );
                                                                          if (result ==
                                                                              null) {
                                                                            return;
                                                                          }

                                                                          final bytes =
                                                                              await result.readAsBytes();
                                                                          final image =
                                                                              await decodeImageFromList(bytes);

                                                                          final message =
                                                                              types.ImageMessage(
                                                                            author:
                                                                                user,
                                                                            createdAt:
                                                                                DateTime.now().millisecondsSinceEpoch,
                                                                            height:
                                                                                image.height.toDouble(),
                                                                            id: const Uuid().v4(),
                                                                            name:
                                                                                result.name,
                                                                            size:
                                                                                bytes.length,
                                                                            uri:
                                                                                result.path,
                                                                            width:
                                                                                image.width.toDouble(),
                                                                          );

                                                                          messages.insert(
                                                                              0,
                                                                              message);
                                                                          setState(
                                                                              () {});
                                                                          selectionHaptic();
                                                                        },
                                                                        icon: const Icon(Icons
                                                                            .image_rounded),
                                                                        label: Text(
                                                                            AppLocalizations.of(context)!.uploadImage)))
                                                          ]));
                                                });
                                          },
                                l10n: ChatL10nEn(
                                    inputPlaceholder:
                                        AppLocalizations.of(context)!
                                            .messageInputPlaceholder,
                                    attachmentButtonAccessibilityLabel:
                                        AppLocalizations.of(context)!
                                            .tooltipAttachment,
                                    sendButtonAccessibilityLabel:
                                        AppLocalizations.of(context)!
                                            .tooltipSend),
                                inputOptions: InputOptions(
                                    keyboardType: TextInputType.multiline,
                                    onTextChanged: (p0) {
                                      setState(() {
                                        sendable = p0.trim().isNotEmpty;
                                      });
                                    },
                                    sendButtonVisibilityMode: desktopFeature()
                                        ? SendButtonVisibilityMode.always
                                        : (sendable)
                                            ? SendButtonVisibilityMode.always
                                            : SendButtonVisibilityMode.hidden),
                                user: user,
                                hideBackgroundOnEmojiMessages: false,
                                theme: (Theme.of(context).brightness ==
                                        Brightness.light)
                                    ? DefaultChatTheme(
                                        backgroundColor:
                                            themeLight().colorScheme.surface,
                                        primaryColor:
                                            themeLight().colorScheme.primary,
                                        attachmentButtonIcon: !multimodal
                                            ? (prefs?.getBool("voiceModeEnabled") ??
                                                    false)
                                                ? Icon(Icons.headphones_rounded,
                                                    color: Theme.of(context)
                                                        .iconTheme
                                                        .color)
                                                : null
                                            : Icon(Icons.add_a_photo_rounded,
                                                color: Theme.of(context).iconTheme.color),
                                        sendButtonIcon: SizedBox(
                                          height: 24,
                                          child: CircleAvatar(
                                              backgroundColor: Theme.of(context)
                                                  .iconTheme
                                                  .color,
                                              radius: 12,
                                              child: Icon(
                                                  Icons.arrow_upward_rounded,
                                                  color: (prefs?.getBool(
                                                              "useDeviceTheme") ??
                                                          false)
                                                      ? Theme.of(context)
                                                          .colorScheme
                                                          .surface
                                                      : null)),
                                        ),
                                        sendButtonMargin: EdgeInsets.zero,
                                        attachmentButtonMargin: EdgeInsets.zero,
                                        inputBackgroundColor: themeLight().colorScheme.onSurface.withAlpha(10),
                                        inputTextColor: themeLight().colorScheme.onSurface,
                                        inputBorderRadius: BorderRadius.circular(32),
                                        inputPadding: const EdgeInsets.all(16),
                                        inputMargin: EdgeInsets.only(left: !desktopFeature(web: true) ? 8 : 6, right: !desktopFeature(web: true) ? 8 : 6, bottom: (MediaQuery.of(context).viewInsets.bottom == 0.0 && !desktopFeature(web: true)) ? 0 : 8),
                                        messageMaxWidth: (MediaQuery.of(context).size.width >= 1000)
                                            ? (MediaQuery.of(context).size.width >= 1600)
                                                ? (MediaQuery.of(context).size.width >= 2200)
                                                    ? 1900
                                                    : 1300
                                                : 700
                                            : 440)
                                    : DarkChatTheme(
                                        backgroundColor: themeDark().colorScheme.surface,
                                        primaryColor: themeDark().colorScheme.primary.withAlpha(40),
                                        secondaryColor: themeDark().colorScheme.primary.withAlpha(20),
                                        attachmentButtonIcon: !multimodal
                                            ? (prefs?.getBool("voiceModeEnabled") ?? false)
                                                ? Icon(Icons.headphones_rounded, color: Theme.of(context).iconTheme.color)
                                                : null
                                            : Icon(Icons.add_a_photo_rounded, color: Theme.of(context).iconTheme.color),
                                        sendButtonIcon: SizedBox(
                                          height: 24,
                                          child: CircleAvatar(
                                              backgroundColor: Theme.of(context)
                                                  .iconTheme
                                                  .color,
                                              radius: 12,
                                              child: Icon(
                                                  Icons.arrow_upward_rounded,
                                                  color: (prefs?.getBool(
                                                              "useDeviceTheme") ??
                                                          false)
                                                      ? Theme.of(context)
                                                          .colorScheme
                                                          .surface
                                                      : null)),
                                        ),
                                        sendButtonMargin: EdgeInsets.zero,
                                        attachmentButtonMargin: EdgeInsets.zero,
                                        inputBackgroundColor: themeDark().colorScheme.onSurface.withAlpha(40),
                                        inputTextColor: themeDark().colorScheme.onSurface,
                                        inputBorderRadius: BorderRadius.circular(32),
                                        inputPadding: const EdgeInsets.all(16),
                                        inputMargin: EdgeInsets.only(left: !desktopFeature(web: true) ? 8 : 6, right: !desktopFeature(web: true) ? 8 : 6, bottom: (MediaQuery.of(context).viewInsets.bottom == 0.0 && !desktopFeature(web: true)) ? 0 : 8),
                                        messageMaxWidth: (MediaQuery.of(context).size.width >= 1000)
                                            ? (MediaQuery.of(context).size.width >= 1600)
                                                ? (MediaQuery.of(context).size.width >= 2200)
                                                    ? 1900
                                                    : 1300
                                                : 700
                                            : 440)),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            drawerEdgeDragWidth: (prefs?.getBool("fixCodeblockScroll") ?? false)
                ? null
                : (desktopLayout(context)
                    ? null
                    : MediaQuery.of(context).size.width),
            drawer: Builder(builder: (context) {
              if (desktopLayoutRequired(context) && !settingsOpen) {
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (Navigator.of(context).canPop()) {
                    Navigator.of(context).pop();
                  }
                });
              }
              return NavigationDrawer(
                  onDestinationSelected: (value) {
                    if (value == 1) {
                    } else if (value == 2) {}
                  },
                  selectedIndex: 1,
                  children: sidebar(context, setState));
            })),
      );
    } catch (e, stackTrace) {
      print('[MainApp] Error in build: $e');
      print('[MainApp] Stack trace: $stackTrace');

      // 显示错误信息
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.red),
              SizedBox(height: 16),
              Text(
                'Error: ${e.toString()}',
                style: TextStyle(color: Colors.red),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  setState(() {});
                },
                child: Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }
  }

  @override
  void dispose() {
    // 停止设备广播服务
    _broadcastService.dispose();
    _deviceService.dispose();
    super.dispose();
  }

  Future<void> _loadKnowledgeBases() async {
    try {
      print('[_loadKnowledgeBases] Starting...');

      // 获取设备ID
      final deviceId = await DeviceIdService().getDeviceId();
      print('[_loadKnowledgeBases] Device ID: $deviceId');

      // 直接使用MultiAgentService获取知识库
      final kbs =
          await MultiAgentService().getKnowledgeBases(deviceId: deviceId);
      print('[_loadKnowledgeBases] Knowledge bases: ${kbs.length}');

      setState(() {
        knowledgeBases = kbs;
        syncedKnowledgeBases = [];
      });

      print('[_loadKnowledgeBases] Complete. Total: ${kbs.length}');
    } catch (e) {
      print('Error loading knowledge bases: $e');
      print('Stack trace: ${StackTrace.current}');
    }
  }

  String _getKnowledgeBaseName(String? kbId) {
    if (kbId == null) return 'Unknown';

    // 查找所有知识库中的名称
    final allKbs = [...knowledgeBases, ...syncedKnowledgeBases];
    final kb = allKbs.firstWhere(
      (kb) => kb['id'] == kbId,
      orElse: () => {'name': 'Unknown'},
    );

    return kb['name'] ?? 'Unknown';
  }

  void _showKnowledgeBaseSelector() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Knowledge Base Settings'),
        content: StatefulBuilder(
          builder: (context, setDialogState) {
            return SizedBox(
              width: double.maxFinite,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // RAG Toggle
                    SwitchListTile(
                      title: const Text('Enable RAG'),
                      subtitle:
                          const Text('Use knowledge base for enhanced answers'),
                      value: useRAG,
                      onChanged: (value) {
                        setDialogState(() {
                          useRAG = value;
                        });
                      },
                    ),
                    const SizedBox(height: 16),

                    // Knowledge Base Selection
                    if (useRAG) ...[
                      const Text(
                        'Select Knowledge Base:',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),

                      // 使用有限高度的容器
                      ConstrainedBox(
                        constraints: BoxConstraints(
                          maxHeight: MediaQuery.of(context).size.height * 0.4,
                        ),
                        child: SingleChildScrollView(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              // 本地知识库
                              if (knowledgeBases.isNotEmpty) ...[
                                const Text('Local Knowledge Bases:',
                                    style: TextStyle(
                                        fontSize: 12, color: Colors.grey)),
                                ...knowledgeBases.map((kb) {
                                  return RadioListTile<String>(
                                    dense: true,
                                    title: Text(kb['name']),
                                    subtitle: kb['description'] != null &&
                                            kb['description']
                                                .toString()
                                                .isNotEmpty
                                        ? Text(kb['description'])
                                        : null,
                                    secondary: Text(
                                        '${kb['document_count'] ?? 0} docs'),
                                    value: kb['id'],
                                    groupValue: selectedKnowledgeBase,
                                    onChanged: (value) {
                                      setDialogState(() {
                                        selectedKnowledgeBase = value;
                                      });
                                    },
                                  );
                                }).toList(),
                              ],

                              // 同步的知识库
                              if (syncedKnowledgeBases.isNotEmpty) ...[
                                const Divider(),
                                const Text('Synced Knowledge Bases:',
                                    style: TextStyle(
                                        fontSize: 12, color: Colors.grey)),
                                ...syncedKnowledgeBases.map((kb) {
                                  return RadioListTile<String>(
                                    dense: true,
                                    title: Row(
                                      children: [
                                        Expanded(child: Text(kb['name'])),
                                        const SizedBox(width: 8),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: Theme.of(context)
                                                .colorScheme
                                                .primaryContainer,
                                            borderRadius:
                                                BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            kb['device_name'] ?? 'Unknown',
                                            style: TextStyle(
                                              fontSize: 10,
                                              color: Theme.of(context)
                                                  .colorScheme
                                                  .onPrimaryContainer,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    subtitle: Text(kb['description'] ?? ''),
                                    secondary: Text(
                                        '${kb['document_count'] ?? 0} docs'),
                                    value: kb['id'],
                                    groupValue: selectedKnowledgeBase,
                                    onChanged: (value) {
                                      setDialogState(() {
                                        selectedKnowledgeBase = value;
                                      });
                                    },
                                  );
                                }).toList(),
                              ],

                              if (knowledgeBases.isEmpty &&
                                  syncedKnowledgeBases.isEmpty)
                                const Center(
                                  child: Padding(
                                    padding: EdgeInsets.all(16.0),
                                    child: Text('No knowledge bases available'),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            );
          },
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context)
                  .push(
                MaterialPageRoute(
                  builder: (context) => const DeviceKnowledgeBaseScreen(),
                ),
              )
                  .then((_) {
                // 返回时刷新
                _loadKnowledgeBases();
              });
            },
            child: const Text('Manage Knowledge Bases'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              // Save settings
              await prefs!.setBool('useRAG', useRAG);
              if (selectedKnowledgeBase != null) {
                await prefs!
                    .setString('selectedKnowledgeBase', selectedKnowledgeBase!);
              } else {
                await prefs!.remove('selectedKnowledgeBase');
              }

              setState(() {});
              Navigator.pop(context);

              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    useRAG && selectedKnowledgeBase != null
                        ? 'RAG enabled with ${_getKnowledgeBaseName(selectedKnowledgeBase)}'
                        : 'RAG disabled',
                  ),
                ),
              );
            },
            child: const Text('Apply'),
          ),
        ],
      ),
    );
  }
}
