# Телеграм бот YourTNotifier #

> Поможет тебе не пропустить изменение стоимости твоих портфелей в ТинькоффИнвестициях за счёт системы уведомлений!

**[Link на Notion с примерами работы бота](https://moored-mozzarella-ae6.notion.site/YourTNotifier-44ef117d2b314783abfc47ef59c4acb1?pvs=4)**

## Стэк ##
* Библиотека aiogram для упрощения сборки бота
* SQLite в качестве основной БД
* Тинькофф InvestAPI для получения информации о ваших инвест-портфелях
  * Предварительно авторизуйтесь в веб-версии ТинькоффИнвестиции и выпустите токен на ReadOnly права ко всем вашим портфелям
  * https://tinkoff.github.io/investAPI/
    <br>
    Установка Python SDK 
    > $ pip install tinkoff-investments
  * метод GetAccounts - сохраняем id и name, а также исключаем "Инвесткопилку"
  * метод GetPortfolio - циклом получаем стоимость каждого портфеля

**<span style="color:yellow">Структура проекта</span>**
* main.py всю основную логику работы бота (команды и джобы)
* invest_requests.py содержит функцию для запроса к InvestAPI
* auth.py там укажите ваши креды

### Логика работы бота ###
<details>
<summary>Детальная логика будет обновлена позже</summary>
<br>

1. Пользователь стартует работу с ботом через /start
   * сохраняем его в таблицу Users со столбцами (id , telegram_id)
   * при повторном вызове /start проверяем наличие пользователя, если уже существует, то ничего не делаем
2. Пользователь через команду /getAccountsData инициирует вызов функции getAccountsAmounts()
   * getAccountsAmounts() находится в файле invest_requests.py , обращается к API и возвращает список кортежей [('account_id','name','amount_rub':int)]. Например [('1111111111', 'Брокерский счёт', 1152465), ('2222222222', 'ИИС', 775363)]
   * записываем полученные значения в таблицу Accounts со столбцами (id , telegram_id, account_id, name, daily_change_rate, amount_rub)
     * daily_change_rate это процентное изменение портфеля за день, при котором он хочет получать уведомление
     * в таблице Accounts значение amount_rub для каждого портфеля сохраняется на конец дня (23:59:00)
     * в таблице Accounts каждому account_id соответствует только одна запись
     * в таблице Accounts каждому telegram_id может соответствовать несколько account_id
   * сообщаем пользователю, что данные успешно сохранены и возвращаем сохранённый список в виде сообщения в боте содержащего все (account_id, name, daily_change_rate, amount_rub)
   * при повторном вызове /getAccountsData проверяем наличие данных, если информация по всем портфелям пользователя уже сохранена, то спрашиваем у него через сообщение в боте, хочет ли он перезаписать данные по портфелям. Далее, если выбрал:
     * "Да", то перезаписываем данные в таблице Accounts повторным вызовом getAccountsAmounts(), в т.ч. зачищаем daily_change_rate
     * "Нет", ничего не делаем, возвращаем сообщение "Перезапись отменена"
3. Посредством сообщения /getCurrentSettings пользователь может получить текущий список из таблицы Accounts (account_id, name, daily_change_rate, amount_rub)
4. Пользователь может совершить ряд действий с портфелем предварительно написав /choosePortfolio в сообщении боту. После вызова функции просим его "Укажите id портфеля, к которому хотите применить изменения" и ожидаем получения account_id
   1. При получении несуществующего account_id пишем ему "Такого портфеля не найдено, попробуйте проверить список написав /getCurrentSettings" и заканчиваем работу функции
   2. При получении существующего account_id даём на выбор 3 функции, которые возвращаем списком в виде сообщения:
      * /getCurrentRate - возвращаем текущее значение daily_change_rate для указанного account_id из таблицы Accounts
      * /setRate - просим его "Укажите процентное изменение портфеля, при котором хотите получать уведомление" и ожидаем сообщения от него
        * при получении НЕ числа пишем "Вы указали НЕ число, напишите /choosePortfolio и попробуйте снова" и заканчиваем работу функции
        * при получении числа со знаком + или - или без, а также целого или дробного с разделителем в виде . или , сохраняем значение daily_change_rate для выбранного account_id в таблицу Accounts. И возвращаем пользователю сообщение "Вы установили (указанный пользователем процент) для (name соответстующего портфеля) в качестве уровня, при котором хотите получать уведомление"
      * /discardRate - сбрасываем установленное значение daily_change_rate для выбранного account_id
5. Когда хотя бы для одного из account_id пользователь установил daily_change_rate мы начинаем выполнять регулярные джобы:
   1. Запросы посредством функции getAccountsAmounts() каждые 5 минут и запись полученных значений в аналог таблицы Accounts с названием AccountsTemporary, только вместе daily_change_rate там столбец actual_change_rate В этой таблице значения перезаписываются при каждом выполнении джобы.
      * Изменение рассчитывается для каждого портфеля с указанным (т.е.!= 0.0) daily_change_rate 
      * по принципу (x2/x1-1).Где:
        * x1 = amount_rub сохранённое в таблице Accounts
        * x2 = amount_rub сохранённое в таблице Accounts_temporary
   2. Далее если (daily_change_rate отрицательное и actual_change_rate меньше) ИЛИ (daily_change_rate положительное и actual_change_rate больше), то:
     * послать сообщение пользователю "Изменение за день по портфелю (name) превысило установленное (daily_change_rate - из таблицы Accounts)"
     * по каждому портфелю(account_id) пользователь получает не более 1го уведомления в день, таким образом если в течение дня мы снова заметим превышение установленного изменения, то мы уже не будем уведомлять пользователя

</details>

**<span style="color:yellow">FunctionalRequirments</span>**

Пользовательские функции бота:
1. /start - Начало работы, регистрация пользователя
2. /getAccountsData - Запросить информацию по портфелям из API. Используйте после start или для сброса данных
3. /getCurrentSettings - Получение ваших текущих настроек
4. /choosePortfolio - Совершение действий с портфелями. Используйте после первичной настройки
5. Провоцирует вызов 3х следующих шагов
   * getCurrentRate - получение текущего установленного процента
   * setRate - установка нового процента (1 на каждый портфель)
   * discardRate - сброс установленного процента

Jobs:
1. Регулярные запросы стоимости портфелей
2. Сравнение значения на 23:50 прошедшего дня с последним полученным значением по каждому портфелю
   * <span style="color:red">Обновление данных для сравнение в конце дня пока не работает</span>.
   * посчитать изменение (x2/x1 - 1) * 100
   * если реальное изменение одинаково по знаку и больше по модулю, чем установленное, то послать сообщение пользователю
   * по каждому портфелю пользователь получает не более 1го уведомления в день
3. Ежедневное обновление значений в таблице Accounts


**Прочее:**
* установка SQLite:
  * cls
  * winget install sqlite.sqlite
* установка DBbrowser:
  * winget install DBBrowserForSQLite.DBBrowserForSQLite