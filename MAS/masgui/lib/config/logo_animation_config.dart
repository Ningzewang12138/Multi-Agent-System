/// Logo动画配置
/// 
/// 这个文件用于配置logo图标的缩放动画效果
class LogoAnimationConfig {
  // 动画缩放参数
  static const double scaleMin = 0.6;   // 最小缩放比例（60%）
  static const double scaleMax = 1.4;   // 最大缩放比例（140%）
  
  // 动画持续时间（毫秒）
  static const int shrinkDuration = 200;  // 缩小动画时长
  static const int expandDuration = 200;  // 放大动画时长
  static const int scaleDuration = 400;   // 整体缩放动画时长
  
  // 更夸张的动画效果（可选）
  static const double dramaticScaleMin = 0.4;   // 更小（40%）
  static const double dramaticScaleMax = 1.6;   // 更大（160%）
  
  // 弹性动画效果
  static const double bounceScaleMin = 0.5;    // 弹性缩小（50%）
  static const double bounceScaleMax = 1.5;    // 弹性放大（150%）
  static const double bounceScaleReturn = 1.1; // 回弹效果（110%）
}
