import os
import sys

print("="*80)
print("🔍 验证实验3所有代码文件")
print("="*80)

base_dir = os.path.dirname(os.path.abspath(__file__))
python_files = [
    "user_behavior_producer.py",
    "recommendation_algorithms.py",
    "simple_deepfm.py",
    "recommendation_fusion.py",
    "advanced_recommendation_consumer.py",
    "realtime_recommendation_service.py",
    "spark_recommendation_trainer.py",
    "recommendation_consumer.py",
]

print(f"\n📁 检查Python文件:")
all_ok = True

for filename in python_files:
    filepath = os.path.join(base_dir, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"  ✅ {filename} - 存在")
        except Exception as e:
            print(f"  ⚠️  {filename} - 读取错误: {e}")
            all_ok = False
    else:
        print(f"  ❌ {filename} - 不存在")
        all_ok = False

print("\n" + "="*80)
print("🧪 测试代码语法:")
print("="*80)

for filename in ["simple_deepfm.py", "recommendation_algorithms.py"]:
    filepath = os.path.join(base_dir, filename)
    if os.path.exists(filepath):
        try:
            result = os.system(f"cd {base_dir} && python -m py_compile {filename} 2>&1")
            if result == 0:
                print(f"  ✅ {filename} - 语法正确")
            else:
                print(f"  ❌ {filename} - 语法错误")
                all_ok = False
        except Exception as e:
            print(f"  ⚠️  {filename} - 测试跳过: {e}")

print("\n" + "="*80)
print("☕ 检查Java/Flink文件:")
print("="*80)

java_dir = os.path.join(base_dir, "..", "code", "flink-ai-project")
java_files = [
    "src/main/java/com/edu/bigdata/FastRecommender.java",
    "src/main/java/com/edu/bigdata/FeatureExtraction.java",
    "src/main/java/com/edu/bigdata/RealtimeRecommendation.java",
    "pom.xml"
]

for filepath in java_files:
    full_path = os.path.join(java_dir, filepath)
    if os.path.exists(full_path):
        print(f"  ✅ {filepath} - 存在")
    else:
        print(f"  ❌ {filepath} - 不存在")
        all_ok = False

print("\n" + "="*80)
if all_ok:
    print("🎉 所有代码文件验证通过！")
else:
    print("⚠️  部分文件有问题，请检查")
print("="*80)
