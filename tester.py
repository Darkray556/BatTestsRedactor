import os # Для прохода по папкам


hedders=[]          # Массив заголовков
comments=[]         # Массив комментариев к заголовкам
tests=[]             # Массив с тестами


# Проверяем коментарии пользователя
def correctComments(arr):

    # Для каждого комментария
    for i in range(len(arr)):

        safe = arr[i]
        # Исправляем за пользователем ошибки синтаксиса
        safe = safe.replace("^", "^^")
        safe = safe.replace("<", "^<")
        safe = safe.replace(">", "^>")
        safe = safe.replace("|", "^|")
        safe = safe.replace("&", "^&")

        arr[i] = safe


# Сортировка строки в файле
def sortline(line):
    result=-1
    if not line.strip():
        result=-2
    # Если строка является заголовком
    elif(line.startswith('// ')):
        result=1

    # Если строка является комментарием
    elif(line.startswith('/ ')):
        result=0

    # Если строка является частью теста
    return result


# Создаем тест
def createTests(tests,testNum):
    # Ничего не делаем, если тестов нет (защита от "pop from empty list")
    if testNum <= 0 or not tests:
        return
    tests.pop(0)            # Удаляем лишний разделитель
    tests.append('*')       # Добавляем разделитель в конец, чтобы выйти из цикла
    for i in range(testNum):
        # Создаем файл с тестом N для записи
        with open(f"test{i+1}.txt", 'w', encoding='utf-8') as testN:

            # Пока не наткнулись на разделитель (и пока массив не пуст)
            while tests and tests[0] !='*':

                # Пишем комментарий, удаляя его после
                testN.write(tests[0])
                tests.pop(0)
            if tests:
                tests.pop(0) # удаляем оставшийся разделитель


# Создаем батник
def createBat(testNum,exename,comments,subcoments):
    # Ничего не делаем, если тестов нет
    if testNum <= 0 or not comments:
        return

    subcoments.pop(0)       #Удаляем лишний разграничитель в масиве с коментариями
    subcoments.append('*')  #Добавляем в конец символ разделителя

    #Вызываем функцию проверки символов для загаловков и комментариев
    correctComments(comments)
    correctComments(subcoments)

    # Создаем файл start.bat для записи
    with open('start.bat','w',encoding='utf-8') as bat:

        bat.write("@echo off\n")                                # Батник при запуске не будет спамить в консоль
        bat.write("if exist results.txt del results.txt\n")     # Удаляем старые результаты перед прогоном
        bat.write(f"set program={exename}\n")                   # Создаем в батнике переменную хранящую имя exe файла с программой пользователя
        bat.write('\n')

        # Для каждого теста
        for i in range(testNum):

            # Маркер начала блока теста (для cleaner.py)
            bat.write("echo ---Result--->> results.txt\n")

            # Пишем заголовок
            bat.write(f"echo [Тест {i+1}] {comments[i]} >> results.txt\n")

            # Если у него нет комментария, то удаляем разделитель
            if(subcoments[0]=='*'):
                subcoments.pop(0)

            # Иначе идем до следующего разделителя
            else:
               while subcoments[0] !='*':

                   # Пишем комментарий с префиксом "/", чтобы cleaner.py мог отличить его от вывода программы
                    bat.write(f"echo / {subcoments[0]} >> results.txt\n")
                    subcoments.pop(0)
               subcoments.pop(0) # удаляем оставшийся разделитель


            bat.write(f"%program% < test{i+1}.txt >> results.txt\n")   # Пишем команду запуска программы с перенаправлением потоков ввода и вывода

            bat.write('\n') # Пустая строка между блоками


# Функция для чтения файла
def sortFile(filename='all_tests.txt'):

    testNum=0 # Количество тестов

    # Открываем файл для чтения
    with open(filename, 'r', encoding='utf-8') as f:

        # Проходимся по каждой строке файла
        for line in f:

            # Вызываем функцию сортировки
            result=sortline(line)

            # Если строка является новым загаловком
            if result ==1:
                # Убираем маркеры и \n, добавляем в массив заголовков
                hedders.append(line[3:].rstrip('\n').rstrip('\r'))

                comments.append('*') # Добавляем маркер разделения в масив коентариев
                tests.append('*')    # Добавляем маркер разделения в масив тестов
                testNum+=1
            elif result ==0:
                # Убираем маркеры и \n, добавляем в массив комментариев
                comments.append(line[2:].rstrip('\n').rstrip('\r'))

            # Если строка является частью теста: добавляем его в массив тестов
            elif result ==-1:
                tests.append(line)

    # Возвращаем кол-во тестов
    return testNum


# Функция запуска полного цикла (для вызова из GUI)
def run_tester(test_file, exe_folder, open_results=True):

    # Очищаем глобальные массивы, чтобы можно было запускать повторно
    hedders.clear()
    comments.clear()
    tests.clear()

    # Читаем файл пользователя со всеми тестами
    testNum=sortFile(test_file)

    # Понятная ошибка вместо загадочного "pop from empty list"
    if testNum == 0:
        raise ValueError(
            "В файле тестов не найдено ни одного теста.\n\n"
            "Каждый тест должен начинаться со строки-заголовка вида:\n"
            "    // Название теста\n\n"
            "Проверьте, что в файле есть хотя бы одна такая строка\n"
            "и что после '//' стоит пробел."
        )

    #Меняем слэши в пути пользователя для перехода
    clean_path = os.path.normpath(exe_folder)

    # Запоминаем текущую рабочую директорию, чтобы потом вернуться
    old_cwd = os.getcwd()

    # Переходим по пути пользователя (в папку с .exe)
    os.chdir(clean_path)

    try:

        # Получаем список файлов в папке с .exe
        filesInDebug=os.listdir(clean_path)

        exeFile=""
        # Ищем наш exe файл
        for file in filesInDebug:
            if file.endswith(".exe"):
                exeFile=file
                break

        if not exeFile:
            raise FileNotFoundError(
                "В указанной папке не найден .exe файл.\n"
                f"Папка: {clean_path}"
            )

        # Создаем тесты
        createTests(tests,testNum)

        # Создаем батник
        createBat(testNum,exeFile,hedders,comments)

        # Запускаем батник
        os.system("start.bat")

        # Открываем результаты
        if open_results:
            os.startfile("results.txt")

    finally:
        # Возвращаемся в исходную директорию
        os.chdir(old_cwd)


# Старый консольный режим (если запускаем tester.py напрямую)
def main():

    user_path=str(input("Введите путь до папки с .exe файлом: "))
    exeFile=""
    # Читаем файл пользователя со всеми тестами
    testNum=sortFile()

    #Меняем слэши в пути пользователя для перехода
    clean_path = os.path.normpath(user_path)

    # Переходим по пути пользователя
    os.chdir(clean_path)

    # Получаем список файлов в папке с .exe
    filesInDebug=os.listdir(clean_path)

    # Ищем наш exe файл
    for file in filesInDebug:
        if file.endswith(".exe"):
            exeFile=file
            break


    # Создаем тесты
    createTests(tests, testNum)

    # Создаем батник
    createBat(testNum, exeFile, hedders, comments)

    # Запускаем батник
    os.system("start.bat")

    # Открываем результаты
    os.startfile("results.txt")


if __name__ == "__main__":
    main()