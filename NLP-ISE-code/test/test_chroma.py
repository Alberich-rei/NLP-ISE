from pathlib import Path

# 检查 Chroma 数据库目录
chroma_dir = Path("chroma_db")
if chroma_dir.exists():
    print("✅ ChromaDB 目录存在")
    
    # 列出数据库文件
    db_files = list(chroma_dir.rglob("*"))
    files = [f for f in db_files if f.is_file()]
    print(f"📁 数据库文件数量: {len(files)}")
    
    # 显示文件列表
    for file in files:
        print(f"   - {file.relative_to(chroma_dir)} ({file.stat().st_size} bytes)")
else:
    print("❌ ChromaDB 目录不存在")