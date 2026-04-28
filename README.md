# Ассистент для создания бизнес-плана

Проект DigitalTeams

**Описание работы скрипта**

- Читаем конфигурацию (адрес API, ключ доступа API-key, папки для промптов и логов) из файла config.yaml
- Читаем описание идей из файла ideas.csv
- Для каждой строки/идеи формируем промпт с подстановкой параметров
- Для всех включенных LLM отправляем запрос 
- Все запросы и ответы логируем в папку logs (формат названия файла - временная метка, модель LLM, req - для запроса, resp - для ответа)

## Требования к первому запуску

Создайте пустой файл .env

### GigaChat

Зарегистрируйтесь на https://developers.sber.ru/studio

В разделе Настройка API будут указаны Данные для авторизации запросов к API (понадобятся на следующем шаге)

В файл .env добавьте следующие строки

GIGA_CLIENT_ID=<ваш_CLIENT_ID>

GIGA_CLIENT_SECRET=<ваш_CLIENT_SECRET>

Установите серты от МинЦифры (инструкция https://developers.sber.ru/docs/ru/gigachat/certificates)

### DeepSeek

Зарегистрируйтесь на https://platform.deepseek.com

Создайте свой API key и укажите его в файл .env

DEEPSEEK_API_KEY=<ваш_API_KEY>

### OpenAI

Зарегистрируйтесь на https://developers.openai.com

Создайте свой API key и укажите его в файл .env

OPENAI_API_KEY=<ваш_API_KEY>

### Конфигурация

Для включения/выключения LLM укажите в файле config.yaml нужное значение:

```
llms:
  configs:
    <LLM>:
      enabled: <true|false>
```

Поддерживаются gigachat для GigaChat, deepseek для DeepSeek, openai для OpenAI (ChatGPT)

### Структура проекта

* config.yaml параметры доступа к LLM
* файл probe.py содержит основной код скрипта
* папка prompts содержит промпты для LLM
* папка logs содержит логи запросов и ответов LLM
