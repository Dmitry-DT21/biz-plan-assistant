# biz-plan-assistant

## Ассистент для создания бизнес-плана
Проект DigitalTeams

### Требования к запуску

#### Зарегистрируйтесь на https://developers.sber.ru/studio

В разделе Настройка API будут указаны Данные для авторизации запросов к API (понадобятся на следующем шаге)

#### Создайте файл .env с содержимым

CLIENT_ID=<ваш_CLIENT_ID>

CLIENT_SECRET=<ваш_CLIENT_SECRET>

#### Установите серты от МинЦифры

Инструкция https://developers.sber.ru/docs/ru/gigachat/certificates

#### Структура проекта

* config.yaml параметры доступа к LLM  
* файл probe.py содержит основной код скрипта
* папка prompts содержит промпты для LLM
* папка logs содержит логи запросов и ответов LLM
