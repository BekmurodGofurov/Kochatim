def main():
    n = int(input("Enter the number of processes -- "))

    bt = []
    for i in range(n):
        bt.append(int(input(f"Enter Burst Time for Process {i} -- ")))

    wt = [0] * n
    tat = [0] * n

    wtavg = 0.0
    tatavg = 0.0

    wt[0] = 0
    tat[0] = bt[0]
    tatavg = float(tat[0])

    for i in range(1, n):
        wt[i] = wt[i - 1] + bt[i - 1]
        tat[i] = tat[i - 1] + bt[i]
        wtavg += wt[i]
        tatavg += tat[i]

    print("\tPROCESS \tBURST TIME \tWAITING TIME\tTURNAROUND TIME")
    for i in range(n):
        print(f"\tP{i}\t\t {bt[i]}\t\t {wt[i]}\t\t {tat[i]}")

    print(f"Average Waiting Time -- {wtavg / n:.6f}")
    print(f"Average Turnaround Time -- {tatavg / n:.6f}")


if __name__ == "__main__":
    main()

