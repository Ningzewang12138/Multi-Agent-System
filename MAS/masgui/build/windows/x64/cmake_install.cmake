# Install script for directory: D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/windows

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "$<TARGET_FILE_DIR:ollama>")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/flutter/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/bitsdojo_window_windows/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/dynamic_color/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/file_selector_windows/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/flutter_tts/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/permission_handler_windows/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/url_launcher_windows/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/volume_controller/cmake_install.cmake")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Runtime" OR NOT CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/ollama.exe")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug" TYPE EXECUTABLE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/ollama.exe")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Pp][Rr][Oo][Ff][Ii][Ll][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/ollama.exe")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile" TYPE EXECUTABLE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/ollama.exe")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/ollama.exe")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release" TYPE EXECUTABLE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/ollama.exe")
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Runtime" OR NOT CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/data/icudtl.dat")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/data" TYPE FILE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/windows/flutter/ephemeral/icudtl.dat")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Pp][Rr][Oo][Ff][Ii][Ll][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/data/icudtl.dat")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/data" TYPE FILE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/windows/flutter/ephemeral/icudtl.dat")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/data/icudtl.dat")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/data" TYPE FILE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/windows/flutter/ephemeral/icudtl.dat")
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Runtime" OR NOT CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/flutter_windows.dll")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug" TYPE FILE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/windows/flutter/ephemeral/flutter_windows.dll")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Pp][Rr][Oo][Ff][Ii][Ll][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/flutter_windows.dll")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile" TYPE FILE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/windows/flutter/ephemeral/flutter_windows.dll")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/flutter_windows.dll")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release" TYPE FILE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/windows/flutter/ephemeral/flutter_windows.dll")
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Runtime" OR NOT CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/bitsdojo_window_windows_plugin.lib;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/dynamic_color_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/file_selector_windows_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/flutter_tts_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/permission_handler_windows_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/url_launcher_windows_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/volume_controller_plugin.dll")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug" TYPE FILE FILES
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/bitsdojo_window_windows/Debug/bitsdojo_window_windows_plugin.lib"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/dynamic_color/Debug/dynamic_color_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/file_selector_windows/Debug/file_selector_windows_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/flutter_tts/Debug/flutter_tts_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/permission_handler_windows/Debug/permission_handler_windows_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/url_launcher_windows/Debug/url_launcher_windows_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/volume_controller/Debug/volume_controller_plugin.dll"
      )
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Pp][Rr][Oo][Ff][Ii][Ll][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/bitsdojo_window_windows_plugin.lib;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/dynamic_color_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/file_selector_windows_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/flutter_tts_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/permission_handler_windows_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/url_launcher_windows_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/volume_controller_plugin.dll")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile" TYPE FILE FILES
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/bitsdojo_window_windows/Profile/bitsdojo_window_windows_plugin.lib"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/dynamic_color/Profile/dynamic_color_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/file_selector_windows/Profile/file_selector_windows_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/flutter_tts/Profile/flutter_tts_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/permission_handler_windows/Profile/permission_handler_windows_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/url_launcher_windows/Profile/url_launcher_windows_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/volume_controller/Profile/volume_controller_plugin.dll"
      )
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/bitsdojo_window_windows_plugin.lib;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/dynamic_color_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/file_selector_windows_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/flutter_tts_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/permission_handler_windows_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/url_launcher_windows_plugin.dll;D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/volume_controller_plugin.dll")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release" TYPE FILE FILES
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/bitsdojo_window_windows/Release/bitsdojo_window_windows_plugin.lib"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/dynamic_color/Release/dynamic_color_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/file_selector_windows/Release/file_selector_windows_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/flutter_tts/Release/flutter_tts_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/permission_handler_windows/Release/permission_handler_windows_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/url_launcher_windows/Release/url_launcher_windows_plugin.dll"
      "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/plugins/volume_controller/Release/volume_controller_plugin.dll"
      )
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Runtime" OR NOT CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug" TYPE DIRECTORY FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/native_assets/windows/")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Pp][Rr][Oo][Ff][Ii][Ll][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile" TYPE DIRECTORY FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/native_assets/windows/")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release" TYPE DIRECTORY FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/native_assets/windows/")
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Runtime" OR NOT CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
    
  file(REMOVE_RECURSE "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/data/flutter_assets")
  
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Pp][Rr][Oo][Ff][Ii][Ll][Ee])$")
    
  file(REMOVE_RECURSE "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/data/flutter_assets")
  
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    
  file(REMOVE_RECURSE "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/data/flutter_assets")
  
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Runtime" OR NOT CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/data/flutter_assets")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Debug/data" TYPE DIRECTORY FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build//flutter_assets")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Pp][Rr][Oo][Ff][Ii][Ll][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/data/flutter_assets")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/data" TYPE DIRECTORY FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build//flutter_assets")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/data/flutter_assets")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/data" TYPE DIRECTORY FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build//flutter_assets")
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Runtime" OR NOT CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Pp][Rr][Oo][Ff][Ii][Ll][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/data/app.so")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Profile/data" TYPE FILE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/app.so")
  elseif(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
     "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/data/app.so")
    if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
      message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
    endif()
    file(INSTALL DESTINATION "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/runner/Release/data" TYPE FILE FILES "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/app.so")
  endif()
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
if(CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_COMPONENT MATCHES "^[a-zA-Z0-9_.+-]+$")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
  else()
    string(MD5 CMAKE_INST_COMP_HASH "${CMAKE_INSTALL_COMPONENT}")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INST_COMP_HASH}.txt")
    unset(CMAKE_INST_COMP_HASH)
  endif()
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "D:/Workspace/Python_Workspace/AIagent-dev/MAS/masgui/build/windows/x64/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
