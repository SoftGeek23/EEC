import random
import os

# Constants based on project specifications
L1_SIZE = 32 * 1024  # 32 KB
L2_SIZE = 256 * 1024  # 256 KB
DRAM_SIZE = 8 * 1024 * 1024 * 1024  # 8 GB
LINE_SIZE = 64  # 64 bytes
L1_ACCESS_TIME = 0.5e-9  # 0.5 ns
L2_ACCESS_TIME = 5e-9  # 5 ns
DRAM_ACCESS_TIME = 50e-9  # 50 ns

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

write_queue_l2 = []
write_queue_dram = []

# Simulation state
time_ns = 0
energy_j = 0
l1_hits = 0
l1_misses = 0
l2_hits = 0
l2_misses = 0

# Cache configuration
l1_assoc = 1  # Direct-mapped
l2_assoc = 4  # Set-associativity
l2_sets = L2_SIZE // (l2_assoc * LINE_SIZE)  # Number of sets in L2

# Cache data structures
l1_cache = [None] * (L1_SIZE // LINE_SIZE)
l2_cache = [[None for _ in range(l2_assoc)] for _ in range(l2_sets)]

# DRAM is not explicitly simulated, we assume everything is a miss to DRAM
def perform_writes(write_queue, write_time, power_active):
    # Perform pending write-backs
    while write_queue:
        address, tag = write_queue.pop(0)
        # Simulate the write-back operation
        global time_ns, energy_j
        time_ns += write_time
        energy_j += power_active * write_time

def simulate_access(address, write=False):
    global time_ns, energy_j
    l1_index = (address // LINE_SIZE) % (L1_SIZE // LINE_SIZE)
    l2_index = (address // LINE_SIZE) % l2_sets
    tag = address // (LINE_SIZE * (L1_SIZE // LINE_SIZE))

    # Check L1 cache
    l1_hit = l1_cache[l1_index] == tag
    if l1_hit:
        # L1 hit
        time_ns += L1_ACCESS_TIME
        energy_j += L1_POWER_RW * L1_ACCESS_TIME
    else:
        # L1 miss, move on to check L2
        l1_cache[l1_index] = tag
        time_ns += L1_ACCESS_TIME
        energy_j += L1_POWER_RW * L1_ACCESS_TIME

        # Simulate L2 cache access
        l2_set = l2_cache[l2_index]
        l2_hit = False
        for i in range(l2_assoc):
            if l2_set[i] == tag:
                # L2 hit
                l2_hit = True
                time_ns += L2_ACCESS_TIME
                energy_j += L2_POWER_RW * L2_ACCESS_TIME + L2_TRANSFER_PENALTY
                break
        
        if not l2_hit:
            # L2 miss, replace a random entry in the set
            replaced_index = random.randint(0, l2_assoc - 1)
            replaced_tag = l2_set[replaced_index]
            if replaced_tag is not None and write:  # Write-back condition
                write_queue_dram.append((l2_index * LINE_SIZE + replaced_tag, replaced_tag))
            l2_set[replaced_index] = tag
            time_ns += L2_ACCESS_TIME + DRAM_ACCESS_TIME
            energy_j += (L2_POWER_RW * L2_ACCESS_TIME) + (DRAM_POWER_RW * DRAM_ACCESS_TIME) + DRAM_TRANSFER_PENALTY

    # Write-back to L2 on L1 update or eviction
    if write:
        if not l1_hit:
            # This implies the L1 cache line being replaced needs to be written back to L2
            evicted_address = (l1_cache[l1_index] << (L1_SIZE // LINE_SIZE).bit_length()) | (l1_index * LINE_SIZE)
            write_queue_l2.append((evicted_address, l1_cache[l1_index]))
    
    l1_cache[l1_index] = tag  # Load the new data into L1

    # Perform pending writes asynchronously (no delay in simulation time for writes)
    perform_writes(write_queue_l2, L2_ACCESS_TIME, L2_POWER_RW)
    perform_writes(write_queue_dram, DRAM_ACCESS_TIME, DRAM_POWER_RW)

    return 'L1 Hit' if l1_hit else ('L2 Hit' if l2_hit else 'DRAM Hit')

perform_writes(write_queue_l2, L2_ACCESS_TIME, L2_POWER_RW)
perform_writes(write_queue_dram, DRAM_ACCESS_TIME, DRAM_POWER_RW)

def calculate_average_access_time(total_time_ns, total_accesses):
    return total_time_ns / total_accesses if total_accesses else float('inf')

# Simulate the cache access for each line in the trace file
total_accesses = 0
with open('./Spec_Benchmark/008.espresso.din', 'r') as trace_file:
    for line in trace_file:
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        access_type, address_hex = parts[0], parts[1]
        address = int(address_hex, 16)
        result = simulate_access(address, write=access_type == '1')
        total_accesses += 1
        if result == 'L1 Hit':
            l1_hits += 1
        elif result == 'L2 Hit':
            l2_hits += 1
        else:
            l1_misses += 1
            l2_misses += 1

average_access_time_ns = calculate_average_access_time(time_ns, total_accesses)

# Print the report
print(f"L1 Cache Hits: {l1_hits}")
print(f"L1 Cache Misses: {l1_misses}")
print(f"L2 Cache Hits: {l2_hits}")
print(f"L2 Cache Misses: {l2_misses}")
print(f"Total simulation time: {time_ns} ns")
print(f"Average memory access time: {average_access_time_ns} ns")
print(f"Total energy consumed: {energy_j} J")