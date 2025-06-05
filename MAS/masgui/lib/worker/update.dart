import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:masgui/worker/clients.dart';
import 'package:masgui/worker/desktop.dart';

import 'haptic.dart';

import 'package:masgui/l10n/gen/app_localizations.dart';

import '../main.dart';

import 'package:flutter_install_referrer/flutter_install_referrer.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:version/version.dart';

// 更新检查已禁用
bool updateChecked = false;
bool updateLoading = false;
String updateStatus = "notAvailable";
String? updateUrl;
String? latestVersion;
String? currentVersion;
String? updateChangeLog;

Future<bool> updatesSupported(Function setState,
    [bool takeAction = false]) async {
  // 更新功能已禁用
  if (takeAction) {
    setState(() {
      updateStatus = "notAvailable";
      updateLoading = false;
    });
  }
  return false;
}

Future<bool> checkUpdate(Function setState) async {
  // 更新检查已禁用
  setState(() {
    updateChecked = true;
    updateLoading = false;
    updateStatus = "notAvailable";
  });
  return false;
}

void updateDialog(BuildContext context, Function title) async {
  await showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
            title:
                Text(AppLocalizations.of(context)!.settingsUpdateDialogTitle),
            content: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(AppLocalizations.of(context)!
                  .settingsUpdateDialogDescription),
              title(AppLocalizations.of(context)!.settingsUpdateChangeLog),
              Flexible(
                  child: SingleChildScrollView(
                      child: Container(
                constraints: const BoxConstraints(maxWidth: 1000),
                child: MarkdownBody(
                    data: updateChangeLog ?? "No changelog given.",
                    shrinkWrap: true),
              )))
            ]),
            actions: [
              TextButton(
                  onPressed: () {
                    selectionHaptic();
                    Navigator.of(context).pop();
                  },
                  child: Text(AppLocalizations.of(context)!
                      .settingsUpdateDialogCancel)),
              TextButton(
                  onPressed: () {
                    selectionHaptic();
                    Navigator.of(context).pop();
                    launchUrl(
                        mode: LaunchMode.inAppBrowserView,
                        Uri.parse(updateUrl!));
                  },
                  child: Text(
                      AppLocalizations.of(context)!.settingsUpdateDialogUpdate))
            ]);
      });
}
