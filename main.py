import os
import csv
import subprocess
from datetime import datetime

class SteamBackup:
    def __init__(self, steam_library, backup_dir, winrar_path, csv_file):
        self.steam_library = steam_library
        self.backup_dir = backup_dir
        self.winrar_path = winrar_path
        self.csv_file = csv_file
        self.backup_data = self.read_backup_csv()

    def read_backup_csv(self):
        backup_data = {}
        if os.path.exists(self.csv_file):
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    appid, buildid, lastupdated, manifest = row
                    backup_data[appid] = (buildid, lastupdated, manifest)
        return backup_data

    def write_backup_csv(self):
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for appid, data in self.backup_data.items():
                writer.writerow([appid, *data])

    def backup_app(self, appid, installdir, buildid, lastupdated, manifest):
        app_dir = os.path.join(self.steam_library, "common", installdir)

        lastupdated_date = datetime.fromtimestamp(int(lastupdated)).strftime('%y%m%d')

        backup_filename = f"[{appid}][{buildid}][{lastupdated_date}][{manifest}]{installdir}.rar"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        self.compress_files(app_dir, backup_path)

        self.backup_data[appid] = (buildid, lastupdated, manifest)
        self.write_backup_csv()

        print(f"App {installdir}:{appid}:{buildid} backed up successfully.")

    def compress_files(self, source, destination):
        subprocess.run([self.winrar_path, "a", "-EP1", "-IBCK", "-K", "-M5", "-MCX", "-MD4G", "-OI", "-S", destination, source])

    def run_backup(self):
        for acf_file in os.listdir(self.steam_library):
            if acf_file.startswith("appmanifest_") and acf_file.endswith(".acf"):
                acf_path = os.path.join(self.steam_library, acf_file)
                self.process_acf_file(acf_path)

    def process_acf_file(self, acf_path):
        with open(acf_path, 'r', encoding='utf-8') as file:
            content = file.read()
            appid = content.split('"appid"\t\t"')[1].split('"')[0]
            installdir = content.split('"installdir"\t\t"')[1].split('"')[0]
            buildid = content.split('"buildid"\t\t"')[1].split('"')[0]
            lastupdated = content.split('"lastupdated"\t\t"')[1].split('"')[0]

            depots_start = content.find('"InstalledDepots"')
            if depots_start != -1:
                depots_end = content.find('}', depots_start)
                depots_content = content[depots_start:depots_end]
                first_manifest = depots_content.split('"manifest"\t\t"')[1].split('"')[0]

            if appid in self.backup_data and self.backup_data[appid][0] == buildid and self.backup_data[appid][1] == lastupdated and self.backup_data[appid][2] == first_manifest:
                print(f"App {installdir}:{appid}:{buildid} already exists.")
                return

            self.backup_app(appid, installdir, buildid, lastupdated, first_manifest)

class SteamBackupFactory:
    @staticmethod
    def create(steam_library, backup_dir, winrar_path, csv_file):
        return SteamBackup(steam_library, backup_dir, winrar_path, csv_file)

# 设置参数
steam_library = r"D:\SteamLibrary\steamapps"
backup_dir = os.path.join(steam_library, "backup")
winrar_path = r"C:\Program Files\WinRAR\WinRAR.exe"
csv_file = os.path.join(backup_dir, "backup.csv")

# 创建 SteamBackup 实例并运行备份
steam_backup = SteamBackupFactory.create(steam_library, backup_dir, winrar_path, csv_file)
steam_backup.run_backup()
