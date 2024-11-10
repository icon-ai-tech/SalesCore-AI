import streamlit as st
import time
import pandas as pd
import base64
import os
import pymongo
import zipfile
import random
from PIL import Image
import warnings

from functions.utils import producer, wait_for_result
from functions.utils import producer_promts, get_response
from functions.utils import get_middle_frame
from functions.utils import generate_ocean_scores, plot_ocean_radar

from config import username, password, mongo_host, mongo_port


################################################################################################################################################

# Кодируем учетные данные в base64 и создаем URL для MongoDB
auth_base64 = base64.b64encode(f"{username}:{password}".encode()).decode()
client = pymongo.MongoClient(
    f"mongodb://{username}:{password}@{mongo_host}:{mongo_port}/?authSource=admin",
    username=username, password=password
)

# Подключаемся к базе данных и коллекции
db = client["data_soc_type"]
collection = db["whisper"]
collection_prompts = db["prompts"]

################################################################################################################################################


image_url = "https://static.tildacdn.com/tild6161-6662-4063-b862-333738316132/Group_13_3.svg"


################################################################################################################################################

mbti_to_ocean = {
    'ESTJ': {'extraversion': (0.6, 0.8), 'neuroticism': (0.3, 0.5), 'agreeableness': (0.4, 0.6), 'conscientiousness': (0.7, 0.9), 'openness': (0.5, 0.7)},
    'ENTJ': {'extraversion': (0.6, 0.8), 'neuroticism': (0.3, 0.5), 'agreeableness': (0.4, 0.6), 'conscientiousness': (0.7, 0.9), 'openness': (0.6, 0.8)},
    'ISTP': {'extraversion': (0.4, 0.6), 'neuroticism': (0.4, 0.6), 'agreeableness': (0.4, 0.6), 'conscientiousness': (0.5, 0.7), 'openness': (0.5, 0.7)},
    'INTP': {'extraversion': (0.2, 0.4), 'neuroticism': (0.4, 0.6), 'agreeableness': (0.3, 0.5), 'conscientiousness': (0.3, 0.5), 'openness': (0.8, 1.0)},
    'ESFJ': {'extraversion': (0.7, 0.9), 'neuroticism': (0.4, 0.6), 'agreeableness': (0.7, 0.9), 'conscientiousness': (0.6, 0.8), 'openness': (0.4, 0.6)},
    'ENFJ': {'extraversion': (0.7, 0.9), 'neuroticism': (0.4, 0.6), 'agreeableness': (0.8, 1.0), 'conscientiousness': (0.6, 0.8), 'openness': (0.7, 0.9)},
    'INFP': {'extraversion': (0.2, 0.4), 'neuroticism': (0.6, 0.8), 'agreeableness': (0.7, 0.9), 'conscientiousness': (0.3, 0.5), 'openness': (0.7, 0.9)},
    'ISFP': {'extraversion': (0.3, 0.5), 'neuroticism': (0.5, 0.7), 'agreeableness': (0.7, 0.9), 'conscientiousness': (0.4, 0.6), 'openness': (0.6, 0.8)},
    'ESTP': {'extraversion': (0.8, 1.0), 'neuroticism': (0.4, 0.6), 'agreeableness': (0.5, 0.7), 'conscientiousness': (0.4, 0.6), 'openness': (0.6, 0.8)},
    'ESFP': {'extraversion': (0.8, 1.0), 'neuroticism': (0.5, 0.7), 'agreeableness': (0.7, 0.9), 'conscientiousness': (0.4, 0.6), 'openness': (0.7, 0.9)},
    'ISFJ': {'extraversion': (0.3, 0.5), 'neuroticism': (0.5, 0.7), 'agreeableness': (0.8, 1.0), 'conscientiousness': (0.6, 0.8), 'openness': (0.4, 0.6)},
    'ISTJ': {'extraversion': (0.3, 0.5), 'neuroticism': (0.4, 0.6), 'agreeableness': (0.5, 0.7), 'conscientiousness': (0.7, 0.9), 'openness': (0.4, 0.6)},
    'ENFP': {'extraversion': (0.7, 0.9), 'neuroticism': (0.5, 0.7), 'agreeableness': (0.6, 0.8), 'conscientiousness': (0.4, 0.6), 'openness': (0.8, 1.0)},
    'ENTP': {'extraversion': (0.7, 0.9), 'neuroticism': (0.4, 0.6), 'agreeableness': (0.4, 0.6), 'conscientiousness': (0.3, 0.5), 'openness': (0.8, 1.0)},
    'INTJ': {'extraversion': (0.2, 0.4), 'neuroticism': (0.3, 0.5), 'agreeableness': (0.3, 0.5), 'conscientiousness': (0.6, 0.8), 'openness': (0.7, 0.9)},
    'INFJ': {'extraversion': (0.2, 0.4), 'neuroticism': (0.5, 0.7), 'agreeableness': (0.8, 1.0), 'conscientiousness': (0.6, 0.8), 'openness': (0.8, 1.0)}
}

vacancies_with_mbti = {
    "Стратегический аналитик": ["INTJ", "ENTJ", "INTP"],
    "Генератор идей и инноваций": ["ENTP", "ENFP", "INTJ"],
    "Дизайнер продуктов для социальной сферы": ["ISFP", "INFJ", "ENFP"],
    "Руководитель проекта": ["ESTJ", "ENTJ", "ISTJ"],
    "Консультант по социальным вопросам": ["INFJ", "ENFJ", "ISFJ"],
    "PR-менеджер или Event-менеджер": ["ESFP", "ENFP", "ESFJ"],
    "Аналитик данных": ["INTJ", "INTP", "ISTJ"],
    "Менеджер по персоналу": ["ENFJ", "ISFJ", "ESFJ"],
    "Эксперт по качеству": ["ISTJ", "ESTJ", "ISTP"],
    "Программист-разработчик": ["INTP", "INTJ", "ISTP"],
    "Менеджер по продажам": ["ESTP", "ESFP", "ENFP"],
    "Координатор социальных проектов": ["INFJ", "ISFJ", "ENFJ"],
    "Мотивирующий тренер или коуч": ["ENFJ", "INFJ", "ENFP"],
    "Инженер-конструктор": ["ISTP", "INTJ", "ISTJ"],
    "Командный координатор": ["ESFJ", "ISFJ", "ESTJ"],
}

mbti_descriptions = {
    "ESTJ": "ESTJ (Режиссер) — Штирлиц. Логико-сенсорный экстраверт, эффективный организатор, ценящий порядок и практичность.",
    "ENTJ": "ENTJ (Полководец) — Джек Лондон. Логико-интуитивный экстраверт, лидер, нацеленный на достижение амбициозных целей.",
    "ISTP": "ISTP (Маэстро) — Габен. Сенсорно-логический интроверт, предпочитает практичность и независимость.",
    "INTP": "INTP (Новатор) — Бальзак. Интуитивно-логический интроверт, мыслитель и аналитик с оригинальными идеями.",
    "ESFJ": "ESFJ (Инструктор) — Гюго. Этически-сенсорный экстраверт, отзывчивый и доброжелательный, заботится о других.",
    "ENFJ": "ENFJ (Коуч) — Гамлет. Этически-интуитивный экстраверт, вдохновляет и поддерживает окружающих.",
    "INFP": "INFP (Философ) — Есенин. Интуитивно-этический интроверт, мечтатель и идеалист с богатым внутренним миром.",
    "ISFP": "ISFP (Артист) — Дюма. Сенсорно-этический интроверт, живет в гармонии с собой и окружающими.",
    "ESTP": "ESTP (Бизнесмен) — Жуков. Сенсорно-логический экстраверт, энергичный и уверенный в себе.",
    "ESFP": "ESFP (Гедонист) — Наполеон. Сенсорно-этический экстраверт, живет настоящим и ценит удовольствие от жизни.",
    "ISFJ": "ISFJ (Покровитель) — Драйзер. Сенсорно-этический интроверт, надежный и заботливый, ценит традиции.",
    "ISTJ": "ISTJ (Следователь) — Максим Горький. Логико-сенсорный интроверт, ответственный и дисциплинированный.",
    "ENFP": "ENFP (Исследователь трендов) — Гексли. Интуитивно-этический экстраверт, любит экспериментировать и исследовать новые идеи.",
    "ENTP": "ENTP (Изобретатель) — Дон Кихот. Интуитивно-логический экстраверт, креативный и любознательный новатор.",
    "INTJ": "INTJ (Стратег) — Робеспьер. Логико-интуитивный интроверт, стратег и планировщик с дальновидностью.",
    "INFJ": "INFJ (Просветленный) — Достоевский. Этически-интуитивный интроверт, глубокомыслящий и чуткий к окружающим."
}

################################################################################################################################################

st.title("Подбор кандидатов на вакансию по типу личности")

st.image(image_url, 
         use_container_width=True)

tab1, tab2 = st.tabs(["Соискатель😎📊", "Работадатель🚀💻"])

################################################################################################################################################

hh = pd.read_csv('hh_dataset.csv')

hh['salary_range'] = (hh['salary_to'] + hh['salary_from'])//2
            
################################################################################################################################################

with tab1:    

    uploaded_file = st.file_uploader("Загрузите видео", type=["mp4"])
    if st.button("Узнать свой тип личности", key='button1'):

        if uploaded_file is not None:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())

            record_id = producer(uploaded_file.name)
            result = wait_for_result(record_id)
            
            st.video(uploaded_file)
            st.success('Видео обработано!', icon="✅")
            
            record_id = producer_promts(result, "Ты должен определить MBTI тип личности для присланного мной текста. В твоём ответе должен быть только четырёхбуквенный тип личности (например, INFJ). Если тип не очевиден, укажи наиболее вероятный. Вот спискок всех типов: ISTJ (логист) — сдержанный и надёжный; ISFJ (защитник) — преданный и ответственный; INFJ (адвокат) — рациональный и сострадательный; INTJ (архитектор) — независимый и уверенный в себе логик; ISTP (мастер) — бесстрашный и целеустремлённый; ISFP (художник) — дружелюбный и чувствительный; INFP (посредник) — творческий и заботливый; INTP (мыслитель) — сдержанный и аналитичный; ESTP (делец) — спонтанный и общительный; ESFP (артист) — оптимистичный и импульсивный; ENFP (чемпион) — активный и общительный; ENTP (спорщик) — смелый и энергичный; ESTJ (режиссёр) — трудолюбивый и практичный; ESFJ (воспитатель) — ответственный и отзывчивый; ENFJ (главный герой) — целеустремлённый и преданный; ENTJ (командир) — инициативный и любящий структуру.")
            response = get_response(record_id)
            
            st.subheader(f"Твой тип: **{response}**")
            st.markdown(mbti_descriptions[response])
            
            st.subheader("Радарная карта личности OCEAN")
            ocean_scores = generate_ocean_scores(response)
            fig = plot_ocean_radar(ocean_scores)
            st.pyplot(fig)
            
            st.subheader("Текст в видео:")
            st.markdown(result)
        else:
            st.write("Пожалуйста, загрузите видео файл.")
        
            
################################################################################################################################################

    
with tab2:
    
    uploaded_zip = st.file_uploader("Выберите ZIP-архив...", type=["zip"], key="uploader1")
    
    vacancy = st.selectbox("Выберите вакансию", list(vacancies_with_mbti.keys()))
    
    if st.button("Подобрать кандидатов"):

        if uploaded_zip is not None:
            # Получаем имя загруженного файла без расширения
            archive_name = os.path.splitext(uploaded_zip.name)[0]
            extraction_path = os.path.join(".", archive_name)  # Путь для распаковки с названием архива
            
            # Создаем папку с именем архива, если она не существует
            if not os.path.exists(extraction_path):
                os.makedirs(extraction_path)
            
            # Распаковка архива в папку с названием архива, игнорируя вложенные пути
            with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    # Убираем пути, оставляя только имя файла
                    filename = os.path.basename(member)
                    if not filename:  # Пропускаем папки
                        continue
                    
                    # Полный путь к файлу назначения
                    target_path = os.path.join(extraction_path, filename)
                    # Сохраняем файл
                    with open(target_path, "wb") as file:
                        file.write(zip_ref.read(member))
            
            
            # Проверка содержимого папки после распаковки
            video_files = [os.path.join(extraction_path, f) for f in os.listdir(extraction_path) if f.endswith(".mp4")]
            st.write("Найденные файлы:", video_files)
            
            # Хранение информации о каждом видео
            video_data = []
            
            for video_file in video_files:
                # Первый этап обработки: получение record_id
                record_id = producer(video_file)
                result = wait_for_result(record_id)
                
                # Второй этап обработки: определение типа MBTI
                record_id = producer_promts(result, "Ты должен определить MBTI тип личности для присланного мной текста. В твоём ответе должен быть только четырёхбуквенный тип личности (например, INFJ). Если тип не очевиден, укажи наиболее вероятный. Вот спискок всех типов: ISTJ (логист) — сдержанный и надёжный; ISFJ (защитник) — преданный и ответственный; INFJ (адвокат) — рациональный и сострадательный; INTJ (архитектор) — независимый и уверенный в себе логик; ISTP (мастер) — бесстрашный и целеустремлённый; ISFP (художник) — дружелюбный и чувствительный; INFP (посредник) — творческий и заботливый; INTP (мыслитель) — сдержанный и аналитичный; ESTP (делец) — спонтанный и общительный; ESFP (артист) — оптимистичный и импульсивный; ENFP (чемпион) — активный и общительный; ENTP (спорщик) — смелый и энергичный; ESTJ (режиссёр) — трудолюбивый и практичный; ESFJ (воспитатель) — ответственный и отзывчивый; ENFJ (главный герой) — целеустремлённый и преданный; ENTJ (командир) — инициативный и любящий структуру.")
                response = get_response(record_id)
                
                # Извлекаем кадр из середины видео
                photo_path = get_middle_frame(video_file)
                
                # Сохранение информации для отображения
                video_data.append({"video_path": video_file, "MBTI": response, "Описание": result, "photo_path": photo_path})
            
            # Конвертируем собранные данные в DataFrame для использования далее
            df = pd.DataFrame(video_data)
            
            st.success('Архив обработан!', icon="✅")
        
            st.balloons()

            # Получаем список подходящих MBTI типов для выбранной вакансии
            suitable_mbti = vacancies_with_mbti[vacancy]
            
            # Фильтруем DataFrame для кандидатов с подходящим MBTI
            filtered_df = df[df["MBTI"].isin(suitable_mbti)]
            
            # Если подходящих меньше 9, добавляем остальных кандидатов
            if len(filtered_df) < 9:
                remaining_df = df[~df.index.isin(filtered_df.index)]
                filtered_df = pd.concat([filtered_df, remaining_df]).head(9)
            else:
                filtered_df = filtered_df.head(9)

            # Вывод кандидатов по колонкам
            columns = [st.columns(3) for _ in range(3)]
            
            for idx, (col, (_, row)) in enumerate(zip([col for cols in columns for col in cols], filtered_df.iterrows())):
                with col:
                    st.markdown(f"### Место {idx + 1}")
                    st.image(row['photo_path'], use_container_width=True)  # Заглушка на случай отсутствия кадра
                    st.markdown(f"**Тип MBTI**: {row['MBTI']}")
                    st.markdown(f"**Описание**: {row['Описание']}")
            
            st.write("---")
            


