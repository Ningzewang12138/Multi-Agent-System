/// MCP工具相关的数据模型

/// MCP工具定义
class Tool {
  final String name;
  final String description;
  final ToolParameters parameters;
  
  Tool({
    required this.name,
    required this.description,
    required this.parameters,
  });
  
  factory Tool.fromJson(Map<String, dynamic> json) {
    // 处理不同的JSON格式
    if (json.containsKey('function')) {
      // OpenAI格式
      final func = json['function'];
      return Tool(
        name: func['name'],
        description: func['description'],
        parameters: ToolParameters.fromJson(func['parameters']),
      );
    } else {
      // 直接格式
      return Tool(
        name: json['name'],
        description: json['description'],
        parameters: ToolParameters.fromJson(json['parameters']),
      );
    }
  }
  
  /// 转换为OpenAI函数调用格式
  Map<String, dynamic> toOpenAIFormat() {
    return {
      'type': 'function',
      'function': {
        'name': name,
        'description': description,
        'parameters': parameters.toJson(),
      },
    };
  }
}

/// 工具参数定义
class ToolParameters {
  final String type;
  final Map<String, ParameterProperty> properties;
  final List<String> required;
  
  ToolParameters({
    this.type = 'object',
    required this.properties,
    required this.required,
  });
  
  factory ToolParameters.fromJson(Map<String, dynamic> json) {
    final props = <String, ParameterProperty>{};
    
    if (json['properties'] != null) {
      (json['properties'] as Map<String, dynamic>).forEach((key, value) {
        props[key] = ParameterProperty.fromJson(value);
      });
    }
    
    return ToolParameters(
      type: json['type'] ?? 'object',
      properties: props,
      required: json['required'] != null 
          ? List<String>.from(json['required'])
          : [],
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'properties': properties.map((key, value) => MapEntry(key, value.toJson())),
      'required': required,
    };
  }
}

/// 参数属性
class ParameterProperty {
  final String type;
  final String? description;
  final dynamic defaultValue;
  final List<dynamic>? enumValues;
  
  ParameterProperty({
    required this.type,
    this.description,
    this.defaultValue,
    this.enumValues,
  });
  
  factory ParameterProperty.fromJson(Map<String, dynamic> json) {
    return ParameterProperty(
      type: json['type'],
      description: json['description'],
      defaultValue: json['default'],
      enumValues: json['enum'] != null ? List.from(json['enum']) : null,
    );
  }
  
  Map<String, dynamic> toJson() {
    final result = <String, dynamic>{
      'type': type,
    };
    
    if (description != null) result['description'] = description;
    if (defaultValue != null) result['default'] = defaultValue;
    if (enumValues != null) result['enum'] = enumValues;
    
    return result;
  }
}
