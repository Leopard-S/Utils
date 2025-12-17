#!/usr/bin/env python3
"""
DDC/CI Monitor Input Source Switcher
显示器输入源切换工具 (带全局快捷键支持)

Requirements / 依赖安装:
    pip install monitorcontrol keyboard

Common Input Source Values / 常见输入源值:
    - VGA-1: 1
    - VGA-2: 2
    - DVI-1: 3
    - DVI-2: 4
    - Composite-1: 5
    - Composite-2: 6
    - S-Video-1: 7
    - S-Video-2: 8
    - Tuner-1: 9
    - Tuner-2: 10
    - Tuner-3: 11
    - Component-1: 12
    - Component-2: 13
    - Component-3: 14
    - DisplayPort-1: 15
    - DisplayPort-2: 16
    - HDMI-1: 17
    - HDMI-2: 18
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from datetime import datetime

# 尝试导入 monitorcontrol
try:
    from monitorcontrol import get_monitors
    from monitorcontrol.vcp import VCPError
    MONITORCONTROL_AVAILABLE = True
except ImportError:
    MONITORCONTROL_AVAILABLE = False

# 尝试导入 keyboard (用于全局热键)
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


class MonitorSwitcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DDC/CI 显示器输入源切换器")
        self.root.geometry("700x580")
        self.root.resizable(True, True)
        
        # 快捷键状态
        self.hdmi_hotkey = None
        self.dp_hotkey = None
        self.hotkeys_enabled = False
        
        # 设置样式
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=2)
        style.configure("Recording.TEntry", fieldbackground="#ffcccc")
        
        self.create_widgets()
        self.check_dependencies()
        
        # 窗口关闭时清理热键
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="DDC/CI 显示器输入源切换器", 
                                font=("Microsoft YaHei", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # 输入控制区域
        control_frame = ttk.LabelFrame(main_frame, text="输入源切换", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # HDMI 行
        hdmi_frame = ttk.Frame(control_frame)
        hdmi_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(hdmi_frame, text="HDMI 端口号:", width=12).pack(side=tk.LEFT)
        self.hdmi_port_var = tk.StringVar(value="17")
        self.hdmi_port_entry = ttk.Entry(hdmi_frame, textvariable=self.hdmi_port_var, width=6)
        self.hdmi_port_entry.pack(side=tk.LEFT, padx=5)
        
        self.hdmi_btn = ttk.Button(hdmi_frame, text="切换到 HDMI", 
                                   command=self.switch_to_hdmi, width=12)
        self.hdmi_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(hdmi_frame, text="快捷键:", width=6).pack(side=tk.LEFT, padx=(10, 0))
        self.hdmi_hotkey_var = tk.StringVar(value="")
        self.hdmi_hotkey_entry = ttk.Entry(hdmi_frame, textvariable=self.hdmi_hotkey_var, width=15)
        self.hdmi_hotkey_entry.pack(side=tk.LEFT, padx=5)
        self.hdmi_hotkey_entry.bind("<FocusIn>", lambda e: self.start_recording("hdmi"))
        self.hdmi_hotkey_entry.bind("<FocusOut>", lambda e: self.stop_recording())
        
        self.hdmi_record_btn = ttk.Button(hdmi_frame, text="录制", width=5,
                                          command=lambda: self.toggle_recording("hdmi"))
        self.hdmi_record_btn.pack(side=tk.LEFT, padx=2)
        
        # DP 行
        dp_frame = ttk.Frame(control_frame)
        dp_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dp_frame, text="DP 端口号:", width=12).pack(side=tk.LEFT)
        self.dp_port_var = tk.StringVar(value="15")
        self.dp_port_entry = ttk.Entry(dp_frame, textvariable=self.dp_port_var, width=6)
        self.dp_port_entry.pack(side=tk.LEFT, padx=5)
        
        self.dp_btn = ttk.Button(dp_frame, text="切换到 DP", 
                                 command=self.switch_to_dp, width=12)
        self.dp_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(dp_frame, text="快捷键:", width=6).pack(side=tk.LEFT, padx=(10, 0))
        self.dp_hotkey_var = tk.StringVar(value="")
        self.dp_hotkey_entry = ttk.Entry(dp_frame, textvariable=self.dp_hotkey_var, width=15)
        self.dp_hotkey_entry.pack(side=tk.LEFT, padx=5)
        self.dp_hotkey_entry.bind("<FocusIn>", lambda e: self.start_recording("dp"))
        self.dp_hotkey_entry.bind("<FocusOut>", lambda e: self.stop_recording())
        
        self.dp_record_btn = ttk.Button(dp_frame, text="录制", width=5,
                                        command=lambda: self.toggle_recording("dp"))
        self.dp_record_btn.pack(side=tk.LEFT, padx=2)
        
        # 快捷键控制区域
        hotkey_control_frame = ttk.Frame(control_frame)
        hotkey_control_frame.pack(fill=tk.X, pady=(10, 5))
        
        self.hotkey_status_var = tk.StringVar(value="🔴 快捷键未启用")
        self.hotkey_status_label = ttk.Label(hotkey_control_frame, 
                                              textvariable=self.hotkey_status_var,
                                              font=("Microsoft YaHei", 9))
        self.hotkey_status_label.pack(side=tk.LEFT, padx=5)
        
        self.enable_hotkey_btn = ttk.Button(hotkey_control_frame, text="🚀 启用快捷键", 
                                            command=self.toggle_hotkeys, width=14)
        self.enable_hotkey_btn.pack(side=tk.LEFT, padx=10)
        
        self.clear_hotkey_btn = ttk.Button(hotkey_control_frame, text="清除快捷键", 
                                           command=self.clear_hotkeys, width=10)
        self.clear_hotkey_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(hotkey_control_frame, text="(提示: 点击输入框后按下想要的快捷键组合)", 
                  foreground="gray", font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=10)
        
        # 自定义端口行
        custom_frame = ttk.Frame(control_frame)
        custom_frame.pack(fill=tk.X, pady=(10, 5))
        
        ttk.Label(custom_frame, text="自定义端口:", width=12).pack(side=tk.LEFT)
        self.custom_port_var = tk.StringVar(value="")
        self.custom_port_entry = ttk.Entry(custom_frame, textvariable=self.custom_port_var, width=6)
        self.custom_port_entry.pack(side=tk.LEFT, padx=5)
        
        self.custom_btn = ttk.Button(custom_frame, text="切换到自定义", 
                                     command=self.switch_to_custom, width=12)
        self.custom_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(custom_frame, text="(常用: 15=DP-1, 16=DP-2, 17=HDMI-1, 18=HDMI-2)", 
                  foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # 操作按钮区域
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        self.get_input_btn = ttk.Button(action_frame, text="📡 获取当前输入端口", 
                                        command=self.get_current_input)
        self.get_input_btn.pack(side=tk.LEFT, padx=5)
        
        self.detect_btn = ttk.Button(action_frame, text="🔍 检测所有显示器", 
                                     command=self.detect_monitors)
        self.detect_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(action_frame, text="🗑️ 清空日志", 
                                    command=self.clear_log)
        self.clear_btn.pack(side=tk.RIGHT, padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="输出日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, 
                                                   font=("Consolas", 10),
                                                   wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))
    
    def check_dependencies(self):
        """检查依赖是否安装"""
        if not MONITORCONTROL_AVAILABLE:
            self.log("❌ 错误: monitorcontrol 库未安装!")
            self.log("请运行以下命令安装:")
            self.log("    pip install monitorcontrol")
            self.log("")
            self.status_var.set("缺少依赖: monitorcontrol")
            
            # 禁用按钮
            self.hdmi_btn.config(state=tk.DISABLED)
            self.dp_btn.config(state=tk.DISABLED)
            self.custom_btn.config(state=tk.DISABLED)
            self.get_input_btn.config(state=tk.DISABLED)
            self.detect_btn.config(state=tk.DISABLED)
        else:
            self.log("✅ monitorcontrol 库已安装")
        
        if not KEYBOARD_AVAILABLE:
            self.log("⚠️ 警告: keyboard 库未安装，快捷键功能不可用")
            self.log("请运行以下命令安装:")
            self.log("    pip install keyboard")
            self.log("注意: Windows 下需要管理员权限运行")
            self.enable_hotkey_btn.config(state=tk.DISABLED)
            self.hdmi_record_btn.config(state=tk.DISABLED)
            self.dp_record_btn.config(state=tk.DISABLED)
        else:
            self.log("✅ keyboard 库已安装 (快捷键功能可用)")
        
        self.log("-" * 50)
        self.log("点击 '检测所有显示器' 开始")
        self.log("设置快捷键: 点击快捷键输入框，然后按下组合键")
    
    # ========== 快捷键录制相关 ==========
    
    def start_recording(self, target):
        """开始录制快捷键"""
        if not KEYBOARD_AVAILABLE:
            return
        
        self.recording_target = target
        self.log(f"⌨️ 正在录制 {'HDMI' if target == 'hdmi' else 'DP'} 快捷键，请按下组合键...")
        
        # 设置录制回调
        keyboard.hook(self.on_key_event)
    
    def stop_recording(self):
        """停止录制"""
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
            except:
                pass
        self.recording_target = None
    
    def on_key_event(self, event):
        """处理按键事件"""
        if event.event_type == "down" and hasattr(self, 'recording_target') and self.recording_target:
            # 获取当前按下的所有键
            hotkey = keyboard.read_hotkey(suppress=False)
            
            # 更新对应的输入框
            if self.recording_target == "hdmi":
                self.root.after(0, lambda: self.hdmi_hotkey_var.set(hotkey))
                self.root.after(0, lambda: self.log(f"✅ HDMI 快捷键已设置为: {hotkey}"))
            elif self.recording_target == "dp":
                self.root.after(0, lambda: self.dp_hotkey_var.set(hotkey))
                self.root.after(0, lambda: self.log(f"✅ DP 快捷键已设置为: {hotkey}"))
            
            # 停止录制
            self.root.after(0, self.stop_recording)
            self.root.after(0, lambda: self.root.focus_set())
    
    def toggle_recording(self, target):
        """切换录制状态"""
        if not KEYBOARD_AVAILABLE:
            messagebox.showwarning("提示", "keyboard 库未安装，无法使用快捷键功能")
            return
        
        entry = self.hdmi_hotkey_entry if target == "hdmi" else self.dp_hotkey_entry
        entry.focus_set()
    
    def toggle_hotkeys(self):
        """启用/禁用快捷键"""
        if not KEYBOARD_AVAILABLE:
            return
        
        if self.hotkeys_enabled:
            self.disable_hotkeys()
        else:
            self.enable_hotkeys()
    
    def enable_hotkeys(self):
        """启用全局快捷键"""
        if not KEYBOARD_AVAILABLE:
            return
        
        hdmi_key = self.hdmi_hotkey_var.get().strip()
        dp_key = self.dp_hotkey_var.get().strip()
        
        if not hdmi_key and not dp_key:
            messagebox.showwarning("提示", "请先设置至少一个快捷键")
            return
        
        try:
            # 先清除现有的热键
            self.disable_hotkeys()
            
            registered = []
            
            if hdmi_key:
                keyboard.add_hotkey(hdmi_key, self.hotkey_switch_hdmi, suppress=True)
                self.hdmi_hotkey = hdmi_key
                registered.append(f"HDMI: {hdmi_key}")
            
            if dp_key:
                keyboard.add_hotkey(dp_key, self.hotkey_switch_dp, suppress=True)
                self.dp_hotkey = dp_key
                registered.append(f"DP: {dp_key}")
            
            self.hotkeys_enabled = True
            self.hotkey_status_var.set("🟢 快捷键已启用")
            self.enable_hotkey_btn.config(text="⏹️ 禁用快捷键")
            
            self.log(f"🚀 全局快捷键已启用: {', '.join(registered)}")
            self.log("   现在可以在任何程序中使用快捷键切换输入源")
            
        except Exception as e:
            self.log(f"❌ 启用快捷键失败: {str(e)}")
            messagebox.showerror("错误", f"启用快捷键失败: {str(e)}\n\n可能需要以管理员身份运行程序")
    
    def disable_hotkeys(self):
        """禁用全局快捷键"""
        if not KEYBOARD_AVAILABLE:
            return
        
        try:
            if self.hdmi_hotkey:
                try:
                    keyboard.remove_hotkey(self.hdmi_hotkey)
                except:
                    pass
                self.hdmi_hotkey = None
            
            if self.dp_hotkey:
                try:
                    keyboard.remove_hotkey(self.dp_hotkey)
                except:
                    pass
                self.dp_hotkey = None
            
            self.hotkeys_enabled = False
            self.hotkey_status_var.set("🔴 快捷键未启用")
            self.enable_hotkey_btn.config(text="🚀 启用快捷键")
            
            if hasattr(self, 'log'):
                self.log("⏹️ 全局快捷键已禁用")
                
        except Exception as e:
            self.log(f"⚠️ 禁用快捷键时出错: {str(e)}")
    
    def clear_hotkeys(self):
        """清除所有快捷键设置"""
        self.disable_hotkeys()
        self.hdmi_hotkey_var.set("")
        self.dp_hotkey_var.set("")
        self.log("🗑️ 已清除所有快捷键设置")
    
    def hotkey_switch_hdmi(self):
        """通过快捷键切换到 HDMI"""
        self.root.after(0, self.switch_to_hdmi)
    
    def hotkey_switch_dp(self):
        """通过快捷键切换到 DP"""
        self.root.after(0, self.switch_to_dp)
    
    # ========== 原有功能 ==========
    
    def log(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def switch_to_hdmi(self):
        """切换到 HDMI"""
        try:
            port = int(self.hdmi_port_var.get())
            self.switch_input_source(port, "HDMI")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的端口号")
    
    def switch_to_dp(self):
        """切换到 DP"""
        try:
            port = int(self.dp_port_var.get())
            self.switch_input_source(port, "DisplayPort")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的端口号")
    
    def switch_to_custom(self):
        """切换到自定义端口"""
        try:
            port = int(self.custom_port_var.get())
            self.switch_input_source(port, "自定义")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的端口号")
    
    def switch_input_source(self, port, name):
        """切换输入源"""
        if not MONITORCONTROL_AVAILABLE:
            return
        
        self.status_var.set(f"正在切换到 {name} (端口 {port})...")
        self.log(f"🔄 尝试切换到 {name} (端口号: {port})")
        
        def do_switch():
            try:
                monitors = get_monitors()
                if not monitors:
                    self.root.after(0, lambda: self.log("⚠️ 未检测到支持 DDC/CI 的显示器"))
                    self.root.after(0, lambda: self.status_var.set("未找到显示器"))
                    return
                
                for i, monitor in enumerate(monitors):
                    try:
                        with monitor:
                            # VCP code 0x60 是输入源选择
                            monitor.set_input_source(port)
                            msg = f"✅ 显示器 {i}: 已切换到 {name} (端口 {port})"
                            self.root.after(0, lambda m=msg: self.log(m))
                    except Exception as e:
                        msg = f"❌ 显示器 {i}: 切换失败 - {str(e)}"
                        self.root.after(0, lambda m=msg: self.log(m))
                
                self.root.after(0, lambda: self.status_var.set("切换完成"))
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ 错误: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set("切换失败"))
        
        threading.Thread(target=do_switch, daemon=True).start()
    
    def get_current_input(self):
        """获取当前输入端口"""
        if not MONITORCONTROL_AVAILABLE:
            return
        
        self.status_var.set("正在获取当前输入...")
        self.log("📡 获取当前输入端口...")
        
        def do_get():
            try:
                monitors = get_monitors()
                if not monitors:
                    self.root.after(0, lambda: self.log("⚠️ 未检测到支持 DDC/CI 的显示器"))
                    self.root.after(0, lambda: self.status_var.set("未找到显示器"))
                    return
                
                for i, monitor in enumerate(monitors):
                    try:
                        with monitor:
                            input_source = monitor.get_input_source()
                            msg = f"📺 显示器 {i}: 当前输入 = {input_source}"
                            self.root.after(0, lambda m=msg: self.log(m))
                    except Exception as e:
                        msg = f"❌ 显示器 {i}: 无法读取 - {str(e)}"
                        self.root.after(0, lambda m=msg: self.log(m))
                
                self.root.after(0, lambda: self.status_var.set("获取完成"))
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ 错误: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set("获取失败"))
        
        threading.Thread(target=do_get, daemon=True).start()
    
    def detect_monitors(self):
        """检测所有显示器"""
        if not MONITORCONTROL_AVAILABLE:
            return
        
        self.status_var.set("正在检测显示器...")
        self.log("🔍 检测支持 DDC/CI 的显示器...")
        
        def do_detect():
            try:
                monitors = get_monitors()
                
                if not monitors:
                    self.root.after(0, lambda: self.log("⚠️ 未检测到支持 DDC/CI 的显示器"))
                    self.root.after(0, lambda: self.log("请确保:"))
                    self.root.after(0, lambda: self.log("  1. 显示器支持 DDC/CI"))
                    self.root.after(0, lambda: self.log("  2. 在显示器 OSD 菜单中启用了 DDC/CI"))
                    self.root.after(0, lambda: self.log("  3. 使用支持 DDC/CI 的线缆连接"))
                    self.root.after(0, lambda: self.status_var.set("未找到显示器"))
                    return
                
                self.root.after(0, lambda: self.log(f"✅ 找到 {len(monitors)} 个显示器"))
                self.root.after(0, lambda: self.log("-" * 50))
                
                for i, monitor in enumerate(monitors):
                    try:
                        with monitor:
                            # 获取当前输入
                            try:
                                current_input = monitor.get_input_source()
                                msg = f"📺 显示器 {i}:"
                                self.root.after(0, lambda m=msg: self.log(m))
                                msg = f"   当前输入源: {current_input}"
                                self.root.after(0, lambda m=msg: self.log(m))
                            except Exception as e:
                                msg = f"📺 显示器 {i}: 无法读取当前输入"
                                self.root.after(0, lambda m=msg: self.log(m))
                            
                            # 尝试获取 VCP 能力
                            try:
                                caps = monitor.get_vcp_capabilities()
                                if caps:
                                    # 查找输入源相关信息
                                    if 'inputs' in caps:
                                        msg = f"   可用输入源: {caps['inputs']}"
                                        self.root.after(0, lambda m=msg: self.log(m))
                                    
                                    # 显示原始能力字符串中的输入信息
                                    raw_caps = str(caps)
                                    if '60' in raw_caps:  # VCP code for input
                                        msg = f"   支持输入源切换 (VCP 0x60)"
                                        self.root.after(0, lambda m=msg: self.log(m))
                            except:
                                pass
                            
                    except Exception as e:
                        msg = f"❌ 显示器 {i}: 错误 - {str(e)}"
                        self.root.after(0, lambda m=msg: self.log(m))
                
                self.root.after(0, lambda: self.log("-" * 50))
                self.root.after(0, lambda: self.log("常见输入源端口号:"))
                self.root.after(0, lambda: self.log("  DisplayPort-1: 15, DisplayPort-2: 16"))
                self.root.after(0, lambda: self.log("  HDMI-1: 17, HDMI-2: 18"))
                self.root.after(0, lambda: self.log("  USB-C: 可能是 15 或 27"))
                self.root.after(0, lambda: self.status_var.set("检测完成"))
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ 错误: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set("检测失败"))
        
        threading.Thread(target=do_detect, daemon=True).start()
    
    def on_closing(self):
        """窗口关闭时的清理"""
        self.disable_hotkeys()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MonitorSwitcherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
