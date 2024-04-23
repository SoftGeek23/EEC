import random
import os

# Constants based on project specifications
L1_DATA_SIZE = 32 * 1024  # 32 KB for data
L1_INST_SIZE = 32 * 1024  # 32 KB for instructions
L2_SIZE = 256 * 1024  # 256 KB
DRAM_SIZE = 8 * 1024 * 1024 * 1024  # 8 GB
LINE_SIZE = 64  # 64 bytes
L1_ACCESS_TIME = 0.5e-9  # 0.5 ns
L2_ACCESS_TIME = 5e-9  # 5 ns
DRAM_ACCESS_TIME = 50e-9  # 50 ns
DRAM_energy_j = 0  # Total energy consumed by DRAM accesses
DRAM_accesses = 0  # Count of DRAM accesses


# Power consumption values
L1_POWER_IDLE = 0.5  # Watts
L1_POWER_RW = 1.0  # Watts
L2_POWER_IDLE = 0.8  # Watts
L2_POWER_RW = 2.0  # Watts
DRAM_POWER_IDLE = 0.8  # Watts
DRAM_POWER_RW = 4.0  # Watts

# Energy penalties
L2_TRANSFER_PENALTY = 5e-12  # 5 pJ
DRAM_TRANSFER_PENALTY = 640e-12  # 640 pJ

# Cache data structures
l1_cache = []
l2_cache = [[None for _ in range(4)] for _ in range(L2_SIZE // (4 * LINE_SIZE))]  # Set associativity of 4
l1_data_cache = [None] * (L1_DATA_SIZE // LINE_SIZE)
l1_inst_cache = [None] * (L1_INST_SIZE // LINE_SIZE)
write_queue_l2 = []
write_queue_dram = []

# Simulation state
time_ns = 0
energy_j = 0
l1_hits = 0
l1_misses = 0
l2_hits = 0
l2_misses = 0
l1_energy_j = 0
l2_energy_j = 0

def perform_writes(write_queue, write_time, power_active):
    global time_ns, energy_j
    while write_queue:
        address, tag = write_queue.pop(0)
        time_ns += write_time
        energy_j += power_active * write_time

def simulate_access(address, write=False, is_instruction=False):
    global time_ns, energy_j, l1_data_hits, l1_data_misses, l1_inst_hits, l1_inst_misses, l2_hits, l2_misses, DRAM_accesses, DRAM_energy_j, l1_data_energy_j, l1_inst_energy_j, l2_energy_j
    l1_cache = l1_inst_cache if is_instruction else l1_data_cache
    l1_energy = l1_inst_energy_j if is_instruction else l1_data_energy_j

    l1_index = (address // LINE_SIZE) % (len(l1_cache))
    l2_index = (address // LINE_SIZE) % len(l2_cache)
    tag = address // (LINE_SIZE * len(l1_cache))

    # Check L1 cache
    l1_hit = l1_cache[l1_index] == tag
    if l1_hit:
        # L1 hit
        time_ns += L1_ACCESS_TIME
        energy_j += L1_POWER_RW * L1_ACCESS_TIME
        l1_energy += L1_POWER_RW * L1_ACCESS_TIME
        if is_instruction:
            l1_inst_hits += 1
            l1_inst_energy_j += L1_POWER_RW * L1_ACCESS_TIME  # Correct cumulative energy addition
        else:
            l1_data_hits += 1
            l1_data_energy_j += L1_POWER_RW * L1_ACCESS_TIME  # Correct cumulative energy addition
    else:
        # L1 miss, move on to check L2
        l1_cache[l1_index] = tag
        time_ns += L1_ACCESS_TIME
        energy_j += L1_POWER_RW * L1_ACCESS_TIME
        l1_energy += L1_POWER_RW * L1_ACCESS_TIME
        if is_instruction:
            l1_inst_misses += 1
            l1_inst_energy_j += L1_POWER_RW * L1_ACCESS_TIME  # Correct cumulative energy addition
        else:
            l1_data_misses += 1
            l1_data_energy_j += L1_POWER_RW * L1_ACCESS_TIME  # Correct cumulative energy addition

        l2_set = l2_cache[l2_index]
        l2_hit = False
        for i in range(len(l2_set)):
            if l2_set[i] == tag:
                # L2 hit
                l2_hit = True
                time_ns += L2_ACCESS_TIME
                energy_j += L2_POWER_RW * L2_ACCESS_TIME + L2_TRANSFER_PENALTY
                l2_hits += 1
                break
        
        if not l2_hit:
            # L2 miss, manage DRAM access
            replaced_index = random.randint(0, len(l2_set) - 1)
            replaced_tag = l2_set[replaced_index]
            l2_set[replaced_index] = tag
            time_ns += L2_ACCESS_TIME + DRAM_ACCESS_TIME
            l2_energy_j += L2_POWER_RW * L2_ACCESS_TIME + L2_TRANSFER_PENALTY
            energy_j += (L2_POWER_RW * L2_ACCESS_TIME) + (DRAM_POWER_RW * DRAM_ACCESS_TIME) + DRAM_TRANSFER_PENALTY
            DRAM_energy_j += DRAM_POWER_RW * DRAM_ACCESS_TIME
            DRAM_accesses += 1
            l2_misses += 1

    return 'L1 Hit' if l1_hit else ('L2 Hit' if l2_hit else 'DRAM Hit')

def calculate_average_access_time(total_time_ns, total_accesses):
    return total_time_ns / total_accesses if total_accesses else float('inf')

associativities = [2, 4, 8]
trace_files = [
    './Spec_Benchmark/008.espresso.din', 
    './Spec_Benchmark/013.spice2g6.din', 
    './Spec_Benchmark/015.doduc.din', 
    './Spec_Benchmark/022.li.din', 
    './Spec_Benchmark/023.eqntott.din', 
    './Spec_Benchmark/026.compress.din', 
    './Spec_Benchmark/034.mdljdp2.din', 
    './Spec_Benchmark/039.wave5.din', 
    './Spec_Benchmark/047.tomcatv.din', 
    './Spec_Benchmark/048.ora.din', 
    './Spec_Benchmark/085.gcc.din', 
    './Spec_Benchmark/089.su2cor.din', 
    './Spec_Benchmark/090.hydro2d.din', 
    './Spec_Benchmark/093.nasa7.din',
    './Spec_Benchmark/094.fpppp.din']

# Open the output file in append mode
# Open the output file in append mode
# Open the output file in append mode
with open('output.txt', 'a') as output_file:
    # Run for each trace file
    for trace_file_path in trace_files:
        print(f"File: {trace_file_path}", file=output_file)
        # Run for each associativity
        for l2_assoc in associativities:
            print(f"Set Associativity: {l2_assoc}", file=output_file)
            # Initialize total values for averages
            total_l1_data_energy_j, total_l1_inst_energy_j, total_l2_energy_j, total_dram_energy_j = 0, 0, 0, 0
            total_time_ns, total_energy_j = 0, 0
            # Run a trace for 10 times to get averages
            for run in range(10):
                # Initialize or reset simulation state
                l1_data_hits, l1_data_misses, l1_inst_hits, l1_inst_misses, l2_hits, l2_misses = 0, 0, 0, 0, 0, 0
                l1_data_energy_j, l1_inst_energy_j, l2_energy_j, dram_energy_j = 0, 0, 0, 0
                time_ns, energy_j = 0, 0

                # Reconfigure cache structures
                l2_sets = L2_SIZE // (l2_assoc * LINE_SIZE)
                l1_data_cache = [None] * (L1_DATA_SIZE // LINE_SIZE)
                l1_inst_cache = [None] * (L1_INST_SIZE // LINE_SIZE)
                l2_cache = [[None for _ in range(l2_assoc)] for _ in range(l2_sets)]

                # Run simulation
                total_accesses = 0
                with open(trace_file_path, 'r') as trace_file:
                    for line in trace_file:
                        parts = line.strip().split()
                        if len(parts) < 2:
                            continue
                        op_type, address_hex = int(parts[0]), parts[1]
                        address = int(address_hex, 16)
                        is_instruction = (op_type == 2)
                        write = (op_type == 1)
                        result = simulate_access(address, write=write, is_instruction=is_instruction)
                        total_accesses += 1
                        if result == 'L1 Hit':
                            if is_instruction:
                                l1_inst_hits += 1
                            else:
                                l1_data_hits += 1
                        elif result == 'L2 Hit':
                            l2_hits += 1
                        else:
                            if is_instruction:
                                l1_inst_misses += 1
                            else:
                                l1_data_misses += 1
                            l2_misses += 1

                # Accumulate results for averaging
                total_l1_data_energy_j += l1_data_energy_j
                total_l1_inst_energy_j += l1_inst_energy_j
                total_l2_energy_j += l2_energy_j
                total_dram_energy_j += dram_energy_j
                total_time_ns += time_ns
                total_energy_j += energy_j

                average_access_time_ns = calculate_average_access_time(time_ns, total_accesses)

                # Output results for the current set associativity
                print(f"L1 Data Cache Hits: {l1_data_hits}, Misses: {l1_data_misses}", file=output_file)
                print(f"L1 Inst Cache Hits: {l1_inst_hits}, Misses: {l1_inst_misses}", file=output_file)
                print(f"L2 Cache Hits: {l2_hits}, Misses: {l2_misses}", file=output_file)
                print(f"L1 Data Energy: {l1_data_energy_j} J, L1 Inst Energy: {l1_inst_energy_j} J", file=output_file)
                print(f"L2 Energy: {l2_energy_j} J, DRAM Energy: {dram_energy_j} J", file=output_file)
                print(f"Total Energy: {energy_j} J", file=output_file)
                print(f"Average Memory Access Time: {average_access_time_ns} ns", file=output_file)
                print(f"Total Time: {time_ns} ns", file=output_file)
                print("\n", file=output_file)

            # Calculate and print averages after 10 runs
            average_l1_data_energy = total_l1_data_energy_j / 10
            average_l1_inst_energy = total_l1_inst_energy_j / 10
            average_l2_energy = total_l2_energy_j / 10
            average_dram_energy = total_dram_energy_j / 10
            average_total_energy = total_energy_j / 10
            average_time = total_time_ns / 10

            # Output averaged results for the current set associativity
            print(f"File: {trace_file_path}, Set Associativity: {l2_assoc}", file=output_file)
            print(f"Average L1 Data Energy: {average_l1_data_energy} J", file=output_file)
            print(f"Average L1 Inst Energy: {average_l1_inst_energy} J", file=output_file)
            print(f"Average L2 Energy: {average_l2_energy} J", file=output_file)
            print(f"Average DRAM Energy: {average_dram_energy} J", file=output_file)
            print(f"Average Total Energy: {average_total_energy} J", file=output_file)
            print(f"Average Simulation Time: {average_time} ns", file=output_file)
            print("\n", file=output_file)
