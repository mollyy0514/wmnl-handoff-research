if __name__ == "__main__":
    def oohooh():
        print("a for {} b for {} c for {}".format(a, b, c))
    print("hello")
    a = 'apple'
    b = 'ball'
    c = 'client'
    oohooh()
    with open("/home/wmnlab/D/database/2022-11-29/tsync/sm07/delta.txt", encoding="utf-8") as f:
        s = f.readline()
    print(float(s))
    print(type(float(s)))

    for i in range(10):
        print(i)
        if i > 5:
            i += 1