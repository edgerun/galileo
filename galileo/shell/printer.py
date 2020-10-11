import io


class Stringer:

    def __init__(self, obj) -> None:
        super().__init__()
        self.obj = obj

    @staticmethod
    def to_string(obj):
        if isinstance(obj, str):
            return obj

        if isinstance(obj, dict):
            return Stringer.to_string([f'{k} = {v}' for k, v in obj.items()])

        if isinstance(obj, (list, tuple)):
            p = StringPrinter()
            for item in obj:
                p.print(item)
            return str(p)

        if callable(obj):
            return Stringer.to_string(obj())

        return str(obj)

    def __str__(self):
        return Stringer.to_string(self.obj).strip()

    def __repr__(self):
        return self.__str__()


class StringPrinter:

    def __init__(self) -> None:
        super().__init__()
        self.out = io.StringIO()

    def print(self, *args, **kwargs):
        print(*args, file=self.out, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.print(*args, **kwargs)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.out.getvalue()


def print_tabular(data, columns=None, widths=None, printer=None):
    if not data and not columns:
        return

    printer = printer or print
    columns = columns or data[0].keys()
    if not widths:
        widths = list()
        for c in columns:
            max_len = len(c)

            for row in data:
                max_len = max(max_len, len(str(row[c])))

            widths.append(-max_len)

    sep = ['-' * abs(i) for i in widths]
    sep = '+-' + '-+-'.join(sep) + '-+'

    row_fmt = ['%%%ds' % widths[i] for i in range(len(widths))]
    row_fmt = '| ' + ' | '.join(row_fmt) + ' |'

    header = tuple(columns)

    printer(sep)
    printer(row_fmt % header)
    printer(sep)

    for record in data:
        row = tuple([record[k] for k in columns])
        printer(row_fmt % row)

    printer(sep)


def sprint_routing_table(table) -> str:
    printer = StringPrinter()

    records = [table.get_routing(service) for service in table.list_services()]

    w = [-25, 20, 9]  # TODO: read from records

    sep = ['-' * abs(i) for i in w]
    sep = '+-' + '-+-'.join(sep) + '-+'

    row_fmt = ['%%%ds' % w[i] for i in range(len(w))]
    row_fmt = '| ' + ' | '.join(row_fmt) + ' |'

    header = ('Service', 'Hosts', 'Weights')

    printer(sep)
    printer(row_fmt % header)
    printer(sep)

    for record in records:
        for i in range(len(record.hosts)):
            ls = (record.service if i == 0 else '', record.hosts[i], record.weights[i])
            printer(row_fmt % ls)
        printer(sep)

    return str(printer)
