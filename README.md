# Articles Parser

Проект Articles Parser предназначен для автоматизации процесса сбора и обработки научных публикаций. Он позволяет автоматически находить статьи в различных источниках, фильтровать их по заданным пользователем критериям, скачивать полные тексты, извлекать содержимое и сохранять результаты для дальнейшего анализа. Парсер универсален и может собирать данные о любых химических или физических свойствах.

## Этапы работы

1. Поиск статей: парсер обращается к выбранным научным базам данных и ресурсам, выполняет поиск публикаций по заданным параметрам.
2. Первичная фильтрация: найденные статьи фильтруются по title + abstract с помощью регулярных выражений.
3. Скачивание: происходит загрузка полных текстов статей.
4. Извлечение текста: из загруженных файлов извлекается текстовое содержимое для последующего анализа.
5. Вторичная фильтрация: полный текст статей фильтруется с помощью регулярных выражений на предмет наличия целевого признака и его единиц измерения.


## Запуск

1. Создайте и активируйте conda-окружение:

```bash
conda create -n articles_parser_env python=3.8 -y
conda activate articles_parser_env
```


2. Установите зависимости через pip:

```bash
pip install -r requirements.txt
```

3. Запуск парсера:

```bash
python cli.py --keywords water viscosity \
    --abstract-filter --abstract-patterns temperature \
    --property-filter names --property-names viscosity "dynamic viscosity" \
    --oa-only --max-per-source 50 --output-dir ./output
```

Параметры можно комбинировать в зависимости от задачи. Скрипт также можно
использовать как библиотеку:

```python
from articles_parser import run_pipeline

run_pipeline(
    keywords=["water", "viscosity"],
    abstract_filter=True,
    abstract_patterns=["temperature"],
    property_names_units_filter="names",
    property_names=["viscosity", "dynamic viscosity"],
    oa_only=True,
    max_per_source=50,
    output_directory="./output",
)
```

