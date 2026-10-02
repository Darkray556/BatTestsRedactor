import os


def clean(flag, user_path, tests):
    """
    Универсальная функция очистки отчета и сверки ответов.
    flag: bool (True - запускать очистку, False - пропустить)
    user_path: str (путь к папке с .exe, где лежит results.txt)
    tests: str (абсолютный путь к файлу all_tests.txt)
    """
    # Если пользователь в интерфейсе НЕ выбрал очистку результатов
    if not flag:
        print("Очистка пропущена по флагу пользователя.")
        return

    # Собираем полные системные пути к файлам логов
    results_full_path = os.path.join(user_path, 'results.txt')
    final_full_path = os.path.join(user_path, 'final.txt')

    # Проверяем, создал ли вообще батник файл результатов, чтобы избежать падения
    if not os.path.exists(results_full_path):
        print(f"❌ Ошибка: Файл {results_full_path} не найден! Сначала запустите батник.")
        return

    # Открываем три файла одновременно
    with open(results_full_path, 'r', encoding='utf-8') as result, \
         open(tests, 'r', encoding='utf-8') as compare, \
         open(final_full_path, 'w', encoding='utf-8') as final:

        # Читаем файлы целиком как большие строки
        results_text = result.read().replace('\r', '')
        compares_text = compare.read().replace('\r', '')

        # Нарезаем файлы на изолированные блоки
        results_parts = results_text.split("---Result---")
        compares_parts = compares_text.split("ожидается:")

        # Безопасно удаляем мусорные куски до самых первых маркеров
        if results_parts:
            results_parts.pop(0)
        if compares_parts:
            compares_parts.pop(0)

        total_tests = min(len(results_parts), len(compares_parts))

        verdict = []

        for i in range(total_tests):

            # === 1. ИЗВЛЕКАЕМ ЧИСТЫЙ ЭТАЛОН ДЛЯ ТЕСТА i ===
            expected_lines = []
            test_str = compares_parts[i].split('\n')
            for line in test_str:
                clean_line = line.strip()
                if clean_line.startswith('/ '):
                    expected_lines.append(" ".join(clean_line.replace('/', '').split()))
                elif clean_line:
                    break

            # === 2. ИЗВЛЕКАЕМ РЕАЛЬНЫЙ ОТВЕТ СИ-ПРОГРАММЫ ДЛЯ ТЕСТА i ===
            real_lines = []
            res_str = results_parts[i].split('\n')
            for line in res_str:
                clean_line = line.strip()
                if "[Тест" in clean_line:
                    break
                words = clean_line.split()
                if words and all(w.replace('-', '').isdigit() for w in words):
                    real_lines.append(" ".join(words))

            # === 3. СВЕРЯЕМ ОЧИЩЕННЫЕ БЛОКИ МЕЖДУ СОБОЙ ===
            expected_block = "\n".join(expected_lines).strip()
            real_block = "\n".join(real_lines).strip()

            verdict.append(f"=========================================\n")
            if real_block == expected_block:
                verdict.append(f"[Тест {i+1}] Вердикт: УСПЕШНО!\n")
            else:
                verdict.append(f"[Тест {i+1}] Вердикт: ОШИБКА (Ответ не совпал)!\n")
                verdict.append(f"  Ожидалось:\n{expected_block}\n")
                verdict.append(f"  Получено Си-программой:\n{real_block}\n")

        verdict.append(f"=========================================\n")

        final.writelines(verdict)
        print(f"✅ Анализ завершен! Успешно сопоставлено и проверено тестов: {total_tests}")


def _split_tests_into_blocks(tests_text):
    """
    Режет файл тестов на блоки [(header, [body_lines]), ...].
    header — текст после '// '.
    """
    blocks = []
    current_header = None
    current_body = []

    for line in tests_text.split('\n'):
        if line.startswith('// '):
            if current_header is not None:
                blocks.append((current_header, current_body))
            current_header = line[3:].strip()
            current_body = []
        elif current_header is not None:
            current_body.append(line)

    if current_header is not None:
        blocks.append((current_header, current_body))

    return blocks


def _extract_expected(body_lines):
    """
    Из тела теста извлекает ожидаемый результат.

    Приоритет:
      1) последний блок { ... } (маркеры на отдельных строках);
      2) строки, начинающиеся с '/ ' (старый синтаксис);
      3) пустой список, если ничего не найдено.
    """
    # --- 1. Ищем ПОСЛЕДНИЙ блок {...} ---
    open_idx = -1
    for i, l in enumerate(body_lines):
        if l.strip() == '{':
            open_idx = i

    if open_idx != -1:
        close_idx = -1
        for i in range(open_idx + 1, len(body_lines)):
            if body_lines[i].strip() == '}':
                close_idx = i
                break
        if close_idx != -1:
            return list(body_lines[open_idx + 1:close_idx])

    # --- 2. Запасной вариант: строки с '/' ---
    expected = []
    for l in body_lines:
        if l.startswith('/ '):
            expected.append(l[2:])
        elif l.startswith('/'):
            expected.append(l[1:])
    return expected


def analyze(results_path, tests_path):
    """
    Парсит results.txt и файл тестов, возвращает список результатов.
    Каждый элемент: {
        'num':      int,
        'name':     str,
        'ok':       bool,
        'expected': str,
        'real':     str,
    }
    Никаких файлов не пишет — только возвращает данные для GUI.
    """
    if not os.path.exists(results_path):
        raise FileNotFoundError(
            f"Файл {results_path} не найден. Сначала запустите тесты."
        )

    with open(results_path, 'r', encoding='utf-8') as f:
        results_text = f.read().replace('\r', '')
    with open(tests_path, 'r', encoding='utf-8') as f:
        tests_text = f.read().replace('\r', '')

    # --- 1. Разбираем файл тестов ---
    blocks = _split_tests_into_blocks(tests_text)
    tests_meta = []
    for header, body in blocks:
        expected_lines = _extract_expected(body)
        # Убираем пустые строки по краям, не трогая середину
        while expected_lines and not expected_lines[0].strip():
            expected_lines.pop(0)
        while expected_lines and not expected_lines[-1].strip():
            expected_lines.pop()

        tests_meta.append({
            'name': header,
            'expected': [l.strip() for l in expected_lines],
        })

    # --- 2. Разбираем results.txt ---
    raw_parts = results_text.split('---Result---')
    blocks_res = [b.strip() for b in raw_parts if b.strip()]

    results = []
    for i, block in enumerate(blocks_res):
        name_from_results = ""
        real_lines = []

        for line in block.split('\n'):
            s = line.strip()
            if s.startswith('[Тест'):
                close = s.find(']')
                if close != -1:
                    name_from_results = s[close + 1:].strip()
                continue
            if s.startswith('/'):
                # Комментарий, эхо из батника — не считаем за вывод
                continue
            if not s:
                continue
            real_lines.append(s)

        meta = tests_meta[i] if i < len(tests_meta) else {'name': '', 'expected': []}
        expected_str = "\n".join(meta['expected']).strip()
        real_str = "\n".join(real_lines).strip()
        raw_name = (meta['name'] or name_from_results or "").strip()
        # Убираем ведущий "Тест N:" / "Тест N." если он уже есть в имени
        import re
        raw_name = re.sub(r'^Тест\s+\d+\s*[:.\-]?\s*', '', raw_name, count=1)
        name = raw_name or f"Тест {i + 1}"

        results.append({
            'num':      i + 1,
            'name':     name,
            'ok':       bool(expected_str) and (real_str == expected_str),
            'expected': expected_str,
            'real':     real_str,
        })

    return results


# =====================================================================
# БЛОК ДЛЯ ИЗОЛИРОВАННОЙ ОТЛАДКИ
if __name__ == '__main__':
    my_home_path = r"C:\Users\admin\source\repos\tester\tester\all_tests.txt"
    my_debug_path = r"C:\Users\admin\source\repos\tester\tester"

    print("=== ЗАПУСК ЧЕКЕРА В РЕЖИМЕ ТЕСТИРОВАНИЯ БЭКЕНДА ===")

    # Вариант 1: старая функция (пишет final.txt)
    # clean(True, my_debug_path, my_home_path)

    # Вариант 2: новая функция (возвращает данные)
    res = analyze(os.path.join(my_debug_path, 'results.txt'), my_home_path)
    for r in res:
        mark = "✓" if r['ok'] else "✗"
        print(f"{mark} Тест {r['num']}: {r['name']}")
        if not r['ok']:
            print(f"    Ожидалось: {r['expected']!r}")
            print(f"    Получено:  {r['real']!r}")

    print("=== ОТЛАДКА ЗАВЕРШЕНА ===")