import os
import requests
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, ttk
import fnmatch
from tqdm import tqdm
import glob

# 添加新函数用于扫描服务器文件
def scan_for_servers(directory=None):
    """扫描目录中的服务器jar文件"""
    if directory is None:
        # 如果没有指定目录，使用当前目录
        directory = os.getcwd()
    
    server_files = []
    # 搜索所有可能的服务器jar文件
    patterns = [
        '*server*.jar',  # Vanilla, Paper 等服务器
        '*forge*.jar',   # Forge 服务器
        '*fabric*.jar',  # Fabric 服务器
        '*spigot*.jar',  # Spigot 服务器
        '*bukkit*.jar'   # Bukkit 服务器
    ]
    
    for pattern in patterns:
        for file in glob.glob(os.path.join(directory, '**', pattern), recursive=True):
            if os.path.isfile(file):
                server_files.append(file)
    
    return server_files

# 添加函数用于加载检测到的服务器
def load_detected_servers():
    """加载检测到的服务器到列表中"""
    detected = scan_for_servers()
    for server in detected:
        if server not in downloaded_servers:
            downloaded_servers.append(server)
    update_server_list()

# 修改 update_server_list 函数
def update_server_list():
    server_listbox.delete(0, tk.END)
    for server in downloaded_servers:
        name = os.path.basename(server)
        directory = os.path.dirname(server)
        server_listbox.insert(tk.END, f"{name} ({directory})")
downloaded_servers = []


def get_minecraft_versions():
    url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return [version["id"] for version in data["versions"]]
    else:
        messagebox.showerror("错误", "无法获取版本列表！")
        return []
    
def download_server_jar(url, save_path):
    try:
        # 创建进度条窗口
        progress_window = Toplevel()
        progress_window.title("下载进度")
        progress_window.geometry("300x150")
        
        # 添加进度标签
        progress_label = tk.Label(progress_window, text="正在下载服务器文件...")
        progress_label.pack(pady=10)
        
        # 添加进度条
        progress_bar = ttk.Progressbar(progress_window, length=200, mode='determinate')
        progress_bar.pack(pady=10)
        
        # 添加百分比标签
        percentage_label = tk.Label(progress_window, text="0%")
        percentage_label.pack(pady=5)
        
        # 获取文件大小并开始下载
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        if response.status_code == 200:
            # 更新进度条最大值
            progress_bar['maximum'] = total_size
            
            # 打开文件并开始下载
            with open(save_path, 'wb') as file:
                downloaded_size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        # 更新进度条和百分比
                        progress = (downloaded_size / total_size) * 100
                        progress_bar['value'] = downloaded_size
                        percentage_label.config(text=f"{progress:.1f}%")
                        progress_window.update()
            
            # 下载完成后的操作
            progress_window.destroy()
            create_eula(os.path.dirname(save_path))
            create_plugins_folder(os.path.dirname(save_path))
            downloaded_servers.append(save_path)
            update_server_list()
            
            # 询问是否启动服务器
            if messagebox.askyesno("下载完成", "服务器下载完成！是否立即启动服务器？"):
                try:
                    # 切换到服务器目录
                    os.chdir(os.path.dirname(save_path))
                    # 启动服务器
                    subprocess.Popen(["java", "-Xmx2G", "-Xms1G", "-jar", save_path, "nogui"])
                    messagebox.showinfo("提示", "服务器正在启动，请稍候...")
                except Exception as e:
                    messagebox.showerror("错误", f"服务器启动失败: {str(e)}\n请确保已安装Java并添加到系统环境变量。")
        else:
            progress_window.destroy()
            messagebox.showerror("错误", f"下载失败，HTTP状态码: {response.status_code}")
            
    except Exception as e:
        try:
            progress_window.destroy()
        except:
            pass
        messagebox.showerror("错误", f"下载过程中出现错误: {str(e)}")
    

def create_eula(server_directory):
    eula_path = os.path.join(server_directory, "eula.txt")
    with open(eula_path, "w") as file:
        file.write("eula=true\n")

def create_plugins_folder(server_directory):
    plugins_path = os.path.join(server_directory, "plugins")
    if not os.path.exists(plugins_path):
        os.makedirs(plugins_path)

def get_custom_server_url(version, server_type):
    if server_type == "Vanilla":
        # 使用 Mojang API 获取具体版本的下载 URL
        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        manifest = requests.get(manifest_url).json()
        for ver in manifest["versions"]:
            if ver["id"] == version:
                version_json = requests.get(ver["url"]).json()
                return version_json["downloads"]["server"]["url"]
    elif server_type == "Fabric":
        # Fabric API 格式更新
        return f"https://meta.fabricmc.net/v2/versions/loader/{version}/0.15.6/server/jar"
    elif server_type == "Paper":
        # Paper API 需要先获取构建号
        build_api = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds"
        builds = requests.get(build_api).json()
        if "builds" in builds and len(builds["builds"]) > 0:
            latest_build = builds["builds"][-1]["build"]
            return f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest_build}/downloads/paper-{version}-{latest_build}.jar"
    elif server_type == "Forge":
        # Forge 需要从其 Maven 仓库获取最新版本
        forge_api = f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/index_{version}.json"
        try:
            forge_data = requests.get(forge_api).json()
            latest = list(forge_data["promos"].keys())[-1]
            forge_version = forge_data["promos"][latest]
            return f"https://maven.minecraftforge.net/net/minecraftforge/forge/{version}-{forge_version}/forge-{version}-{forge_version}-installer.jar"
        except:
            return None
    return None


def run_minecraft_server(server_path):
    try:
        subprocess.run(["java", "-Xmx2G", "-Xms1G", "-jar", server_path, "nogui"], check=True)
    except Exception as e:
        messagebox.showerror("错误", f"服务器启动失败: {e}")

def start_selected_server():
    selected_index = server_listbox.curselection()
    if not selected_index:
        messagebox.showwarning("警告", "请选择要启动的服务器！")
        return
    server_path = downloaded_servers[selected_index[0]]
    if os.path.exists(server_path):
        run_minecraft_server(server_path)
    else:
        messagebox.showerror("错误", "服务器文件不存在！")

def manage_plugins():
    selected_index = server_listbox.curselection()
    if not selected_index:
        messagebox.showwarning("警告", "请选择要管理的服务器！")
        return
    server_path = os.path.dirname(downloaded_servers[selected_index[0]])
    plugins_path = os.path.join(server_path, "plugins")
    if os.path.exists(plugins_path):
        os.startfile(plugins_path)
    else:
        messagebox.showerror("错误", "该服务器不支持插件！")
# 创建GUI窗口
root = tk.Tk()
root.title("Minecraft 服务器管理器")
root.geometry("500x400")

# Global variables moved here
versions = get_minecraft_versions()
version_var = tk.StringVar(root)
if versions:
    version_var.set(versions[0])
server_type_var = tk.StringVar(value="Vanilla")
server_types = ["Vanilla", "Fabric", "Forge", "Paper"]
search_var = tk.StringVar(root)
# At the top level with other global variables
versions = get_minecraft_versions()
version_var = tk.StringVar(root)
if versions:
    version_var.set(versions[0])
server_type_var = tk.StringVar(value="Vanilla")
server_types = ["Vanilla", "Fabric", "Forge", "Paper"]
search_var = tk.StringVar(root)  # Add this line

def open_download_window():
    download_window = Toplevel(root)
    download_window.title("下载服务器")
    download_window.geometry("500x300")
    
    global entry_path, search_var, version_menu  # Add version_menu as global
    
    tk.Label(download_window, text="搜索 Minecraft 服务器版本 (支持通配符 * ?):").pack()
    search_var = tk.StringVar()
    search_var.trace("w", update_version_list)
    search_entry = tk.Entry(download_window, textvariable=search_var, width=40)
    search_entry.pack()
    
    version_menu = tk.OptionMenu(download_window, version_var, *versions)  # Store in global variable
    version_menu.pack()
    
    tk.Label(download_window, text="选择服务器类型:").pack()
    server_type_menu = tk.OptionMenu(download_window, server_type_var, *server_types)
    server_type_menu.pack()
    
    tk.Label(download_window, text="选择保存路径:").pack()
    entry_path = tk.Entry(download_window, width=40)
    entry_path.pack()
    tk.Button(download_window, text="浏览", command=select_download_path).pack()
    
    tk.Button(download_window, text="下载服务器", command=lambda: start_download(download_window)).pack()

def start_download(window):
    version = version_var.get()
    server_type = server_type_var.get()
    save_path = entry_path.get()
    
    if not save_path:
        messagebox.showwarning("警告", "请选择保存路径！")
        return
        
    if not version:
        messagebox.showwarning("警告", "请选择服务器版本！")
        return
        
    url = get_custom_server_url(version, server_type)
    if url:
        window.destroy()  # 关闭下载窗口
        download_server_jar(url, save_path)
    else:
        messagebox.showerror("错误", "无法获取服务器下载链接！")
def select_download_path():
    file_path = filedialog.asksaveasfilename(defaultextension=".jar", filetypes=[("JAR 文件", "*.jar")])
    entry_path.delete(0, tk.END)
    entry_path.insert(0, file_path)

def update_version_list(*args):
    search_text = search_var.get().lower()
    filtered_versions = [v for v in versions if fnmatch.fnmatch(v.lower(), search_text.replace("*", "*").replace("?", "?"))]
    version_menu['menu'].delete(0, 'end')
    for version in filtered_versions:
        version_menu['menu'].add_command(label=version, command=tk._setit(version_var, version))
    if filtered_versions:
        version_var.set(filtered_versions[0])
    else:
        version_var.set("")

def update_server_list():
    server_listbox.delete(0, tk.END)
    for server in downloaded_servers:
        server_listbox.insert(tk.END, os.path.basename(server))



tk.Label(root, text="已下载的服务器:").pack()
server_listbox = tk.Listbox(root, width=50, height=10)
server_listbox.pack()
tk.Button(root, text="启动选定服务器", command=start_selected_server).pack()
tk.Button(root, text="管理插件/模组", command=manage_plugins).pack()
tk.Button(root, text="下载服务器", command=open_download_window).pack()
print("请先创建服务器保存文件夹，然后再下载服务器！")

# 在主窗口中添加扫描按钮
scan_button = tk.Button(root, text="扫描本地服务器", command=load_detected_servers)
scan_button.pack()

# 程序启动时自动扫描一次
load_detected_servers()




root.mainloop()
