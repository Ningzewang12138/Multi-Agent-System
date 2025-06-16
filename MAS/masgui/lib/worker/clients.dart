import 'dart:io';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:ollama_dart/ollama_dart.dart' as llama;

import '../main.dart';

class BayminHttpOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    return super.createHttpClient(context)
      ..badCertificateCallback = (_, __, ___) => true;
  }
}

final httpClient = http.Client();
llama.OllamaClient get BayminClient => llama.OllamaClient(
    headers: (jsonDecode(prefs!.getString("hostHeaders") ?? "{}") as Map)
        .cast<String, String>(),
    baseUrl: "$host/api",
    client: httpClient);
