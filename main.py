import os
import json
import csv
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class ConfigError(Exception):
    """Custom exception for configuration errors"""

class SteamBackup:
    def __init__(self, steam_library_steamapps: str, backup_dir: str, winrar_path: str, json_file: str):
        self.steam_library_steamapps = Path(steam_library_steamapps)
        self.backup_dir = Path(backup_dir)
        self.winrar_path = Path(winrar_path)
        self.json_file = Path(json_file)
        
        self._validate_paths()
        self._convert_legacy_csv()
        self.backup_data = self._read_backup_json()

    def _validate_paths(self) -> None:
        """Validate essential paths exist"""
        if not self.steam_library_steamapps.exists():
            raise FileNotFoundError(f"Steam library not found: {self.steam_library_steamapps}")
        if not self.winrar_path.exists():
            raise FileNotFoundError(f"WinRAR executable not found: {self.winrar_path}")
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _convert_legacy_csv(self) -> None:
        """Convert existing CSV backup to JSON format"""
        csv_path = self.backup_dir / "backup.csv"
        if not csv_path.exists():
            return

        try:
            backup_data = {}
            with csv_path.open('r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    appid, buildid, lastupdated, manifest = row
                    backup_data[appid] = {
                        'buildid': buildid,
                        'lastupdated': lastupdated,
                        'manifest': manifest
                    }

            with self.json_file.open('w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2)

            csv_path.rename(csv_path.with_suffix('.csv.old'))
            print(f"Converted legacy CSV to JSON: {csv_path} -> {self.json_file}")
        except Exception as e:
            print(f"Error converting legacy CSV: {str(e)}")

    def _read_backup_json(self) -> Dict[str, Dict[str, str]]:
        """Read backup data from JSON file"""
        if not self.json_file.exists():
            return {}

        try:
            with self.json_file.open('r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading JSON backup file: {str(e)}")
            return {}

    def _write_backup_json(self) -> None:
        """Write backup data to JSON file"""
        with self.json_file.open('w', encoding='utf-8') as f:
            json.dump(self.backup_data, f, indent=2, ensure_ascii=False)

    def backup_app(self, appid: str, installdir: str, buildid: str, 
                  lastupdated: str, manifest: str) -> None:
        """Backup a single Steam application"""
        app_dir = self.steam_library_steamapps / "common" / installdir
        if not app_dir.exists():
            print(f"Install directory not found: {app_dir}")
            return

        lastupdated_date = datetime.fromtimestamp(int(lastupdated)).strftime('%y%m%d')
        backup_filename = f"[{appid}][{buildid}][{lastupdated_date}][{manifest}]{installdir}.rar"
        backup_path = self.backup_dir / backup_filename

        self._compress_files(app_dir, backup_path)

        self.backup_data[appid] = {
            'buildid': buildid,
            'lastupdated': lastupdated,
            'manifest': manifest
        }
        self._write_backup_json()

        print(f"Backup successful: {installdir} ({appid})")

    def _compress_files(self, source: Path, destination: Path) -> None:
        """Compress files using WinRAR with specified settings"""
        try:
            subprocess.run([
                str(self.winrar_path),
                "a", "-ep1", "-ibck", "-k", "-m5", 
                "-mcx", "-md4G", "-oi", "-s",
                str(destination), str(source)
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Compression failed: {str(e)}")
            raise

    def run_backup(self) -> None:
        """Main backup processing method"""
        for acf_file in self.steam_library_steamapps.glob("appmanifest_*.acf"):
            self._process_acf_file(acf_file)

    def _process_acf_file(self, acf_path: Path) -> None:
        """Process a single appmanifest file"""
        try:
            content = acf_path.read_text(encoding='utf-8')
            app_data = self._parse_acf_content(content)
            
            if self._is_backup_current(app_data):
                print(f"Backup current: {app_data['installdir']} ({app_data['appid']})")
                return

            self.backup_app(**app_data)
        except Exception as e:
            print(f"Error processing {acf_path.name}: {str(e)}")

    def _parse_acf_content(self, content: str) -> Dict[str, str]:
        """Parse ACF file content into application data"""
        fields = {
            'appid': '"appid"\t\t"',
            'installdir': '"installdir"\t\t"',
            'buildid': '"buildid"\t\t"',
            'lastupdated': '"lastupdated"\t\t"'
        }

        data = {}
        for key, pattern in fields.items():
            try:
                data[key] = content.split(pattern)[1].split('"')[0]
            except IndexError:
                raise ValueError(f"Missing {key} field in ACF file")

        try:
            depots_section = content.split('"InstalledDepots"')[1]
            data['manifest'] = depots_section.split('"manifest"\t\t"')[1].split('"')[0]
        except IndexError:
            raise ValueError("Missing manifest in InstalledDepots section")

        return data

    def _is_backup_current(self, app_data: Dict[str, str]) -> bool:
        """Check if existing backup is current"""
        existing = self.backup_data.get(app_data['appid'])
        if not existing:
            return False

        return (existing['buildid'] == app_data['buildid'] and
                existing['lastupdated'] == app_data['lastupdated'] and
                existing['manifest'] == app_data['manifest'])

def load_config(config_path: Path) -> Dict[str, str]:
    """Load configuration from JSON file"""
    try:
        content = config_path.read_text(encoding='utf-8')
        config = json.loads(content)
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file: {str(e)}")

    required = ['steam_library_steamapps', 'winrar_path']
    for key in required:
        if key not in config:
            raise ConfigError(f"Missing required config key: {key}")

    return config

def main():
    try:
        config_path = Path("config.json")
        config = load_config(config_path)
        
        steam_library_steamapps = Path(config['steam_library_steamapps'])
        backup_dir = steam_library_steamapps / "backup"
        winrar_path = Path(config['winrar_path'])
        json_file = backup_dir / "backup.json"

        backup = SteamBackup(
            steam_library_steamapps=steam_library_steamapps,
            backup_dir=backup_dir,
            winrar_path=winrar_path,
            json_file=json_file
        )
        backup.run_backup()

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
