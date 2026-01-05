# import requests
# import time
# import zipfile

# api_key = 'eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiI2ODgwMDE1MiIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2NzYyODgzOSwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiIiwib3BlbklkIjpudWxsLCJ1dWlkIjoiZGExZDI4YzEtNWE0Ny00NDhmLTg2YWItYjU3MmM2OTdkMGMyIiwiZW1haWwiOiIiLCJleHAiOjE3Njg4Mzg0Mzl9.CJBXnd746T_SvaDYamlffaRlWxEZ6lmpjpga0dfH_e6QkBlv64Q5WsjedvcJpaqyjeR1IO4ZXIvPBfk1TTxTqA'

# # 调用Mineru在线api接口进行文档解析，需要先将文档上传至url
# def get_task_id(file_name):
#     url='https://mineru.net/api/v4/extract/task'
#     header = {
#         'Content-Type':'application/json',
#         "Authorization":f"Bearer {api_key}".format(api_key)
#     }
#     pdf_url = 'https://vl-image.oss-cn-shanghai.aliyuncs.com/pdf/' + file_name
#     data = {
#         'url':pdf_url,
#         'is_ocr':True,
#         'enable_formula': False,
#     }

#     res = requests.post(url,headers=header,json=data)
#     print(res.status_code)
#     print(res.json())
#     print(res.json()["data"])
#     task_id = res.json()["data"]['task_id']
#     return task_id

# def get_result(task_id):
#     url = f'https://mineru.net/api/v4/extract/task/{task_id}'
#     header = {
#         'Content-Type':'application/json',
#         "Authorization":f"Bearer {api_key}".format(api_key)
#     }

#     while True:
#         res = requests.get(url, headers=header)
#         result = res.json()["data"]
#         print(result)
#         state = result.get('state')
#         err_msg = result.get('err_msg', '')
#         # 如果任务还在进行中，等待后重试
#         if state in ['pending', 'running']:
#             print("任务未完成，等待5秒后重试...")
#             time.sleep(5)
#             continue
#         # 如果有错误，输出错误信息
#         if err_msg:
#             print(f"任务出错: {err_msg}")
#             return
#         # 如果任务完成，下载文件
#         if state == 'done':
#             full_zip_url = result.get('full_zip_url')
#             if full_zip_url:
#                 local_filename = f"{task_id}.zip"
#                 print(f"开始下载: {full_zip_url}")
#                 r = requests.get(full_zip_url, stream=True)
#                 with open(local_filename, 'wb') as f:
#                     for chunk in r.iter_content(chunk_size=8192):
#                         if chunk:
#                             f.write(chunk)
#                 print(f"下载完成，已保存到: {local_filename}")
#                 # 下载完成后自动解压
#                 unzip_file(local_filename)
#             else:
#                 print("未找到 full_zip_url，无法下载。")
#             return
#         # 其他未知状态
#         print(f"未知状态: {state}")
#         return

# # 解压zip文件的函数
# def unzip_file(zip_path, extract_dir=None):
#     """
#     解压指定的zip文件到目标文件夹。
#     :param zip_path: zip文件路径
#     :param extract_dir: 解压目标文件夹，默认为zip同名目录
#     """
#     if extract_dir is None:
#         extract_dir = zip_path.rstrip('.zip')
#     with zipfile.ZipFile(zip_path, 'r') as zip_ref:
#         zip_ref.extractall(extract_dir)
#     print(f"已解压到: {extract_dir}")

# if __name__ == "__main__":
#     file_name = '【财报】中芯国际：中芯国际2024年年度报告.pdf'
#     task_id = get_task_id(file_name)
#     print('task_id:',task_id)
#     get_result(task_id)


# src/pdf_mineru.py
from __future__ import annotations
import os
import subprocess
from pathlib import Path
import shutil

class MineruLocalError(RuntimeError):
    pass

def convert_local(pdf_path: str | Path, out_dir: str | Path, *, backend: str = "pipeline", source: str = "local", timeout: int = 60*60):
    """
    调用本地 mineru CLI，把 pdf_path 转换到 out_dir。
    成功返回 out_dir（Path）。
    """
    pdf_path = Path(pdf_path).expanduser().resolve()
    out_dir = Path(out_dir).expanduser().resolve()
    print(f"输出目录: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")

    env = os.environ.copy()
    env.setdefault("MINERU_MODEL_SOURCE", source)

    cmd = [
        "mineru",
        "-p", str(pdf_path),
        "-o", str(out_dir),
        "-b", backend,
        "--source", source,
    ]

    proc = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if proc.returncode != 0:
        raise MineruLocalError(
            "MinerU 本地转换失败\n"
            f"cmd: {' '.join(cmd)}\n"
            f"returncode: {proc.returncode}\n"
            f"stdout:\n{proc.stdout[-4000:]}\n"
            f"stderr:\n{proc.stderr[-4000:]}\n"
        )

    return out_dir




def flatten_md_and_cleanup(tar_dir: str | Path):
    """
    递归遍历 tar_dir：
    - 将所有 .md 文件移动到 tar_dir 根目录
    - 删除其余所有文件和子目录

    :param tar_dir: 目标目录路径
    """
    tar_dir = Path(tar_dir).resolve()

    if not tar_dir.exists() or not tar_dir.is_dir():
        raise ValueError(f"不是有效目录: {tar_dir}")

    md_files = []
    # 收集所有 md 文件（不包含根目录已存在的 md）
    for p in tar_dir.rglob("*.md"):
        if p.parent != tar_dir:
            md_files.append(p)

    # 移动 md 文件到根目录（处理重名）
    for md in md_files:
        target = tar_dir / md.name

        # 如果重名，自动加后缀
        if target.exists():
            stem = md.stem
            suffix = md.suffix
            i = 1
            while True:
                new_name = f"{stem}_{i}{suffix}"
                target = tar_dir / new_name
                if not target.exists():
                    break
                i += 1

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(md), str(target))

    #  删除根目录下除 md 以外的所有内容
    for p in tar_dir.iterdir():
        if p.is_file():
            if p.suffix.lower() != ".md":
                p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)

    print(f"完成整理：保留 {len(list(tar_dir.glob('*.md')))} 个 Markdown 文件")
