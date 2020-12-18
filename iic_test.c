
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <time.h>

#define writeAddress(iic,addr,RWbar) iic[0x108/4] = 0x100 | ((addr << 1) & 0xFE) | (RWbar & 0x1);

void setup_iic(uint32_t *iic)
{
	iic[0x40/4] = 0xA; // Reset the IIC core
	iic[0x120/4] = 0xF; // Set the RX FIFO depth to maximum
	iic[0x100/4] = 0x2; // Flush the TX FIFO
	iic[0x100/4] = 0x1; // Enable the IIC core
}

void push_TX_FIFO(uint32_t *iic, uint32_t value, int start, int stop)
{
	iic[0x108/4] = ((start & 1) << 8) | ((stop & 1) << 9) | value;
}

void write_address(uint32_t *iic, uint32_t address, uint32_t read_writebar)
{
	push_TX_FIFO(iic, ((address & 0x7F) << 1) | (read_writebar & 1), 1, 0);
}

void wait_for_busy(uint32_t *iic)
{
	int i = 0;
	while ((iic[0x104/4] & 0x4) != 0x4) {
		i++;
		if (i >= 10000) break;
		usleep(10);
	}
}

void wait_for_not_busy(uint32_t *iic)
{
	while ((iic[0x104/4] & 0x4) != 0x0) usleep(10);
}

void write_ECONT(uint32_t *iic, uint32_t ECONT_address, uint32_t indirect_address, uint32_t *data, uint32_t Nbytes)
{
	int i;
	write_address(iic, (0b010 << 4) | (ECONT_address & 0xF), 0);
	//wait_for_busy(iic);
	push_TX_FIFO(iic, ((indirect_address & 0xFF00) >> 8), 0, 0);
	push_TX_FIFO(iic, (indirect_address & 0xFF), 0, 0);
	for(i = 0; i < Nbytes; i++)
		push_TX_FIFO(iic, data[i], 0, (i == (Nbytes-1)) ? 1 : 0);
	wait_for_not_busy(iic);
}

void read_ECONT(uint32_t *iic, uint32_t ECONT_address, uint32_t indirect_address, uint32_t *data, uint32_t Nbytes)
{
	int i;
	write_address(iic, (0b010 << 4) | (ECONT_address & 0xF), 0);
	wait_for_busy(iic);
	push_TX_FIFO(iic, ((indirect_address & 0xFF00) >> 8), 0, 0);
	push_TX_FIFO(iic, (indirect_address & 0xFF), 0, 1);
	wait_for_not_busy(iic);

	write_address(iic, (0b010 << 4) | (ECONT_address & 0xF), 1);
	wait_for_busy(iic);
	push_TX_FIFO(iic, Nbytes & 0xFF, 0, 1);
	wait_for_not_busy(iic);

	i = 0;
	while ((iic[0x104/4] & 0x40) != 0x40)
	{
		data[i] = iic[0x10C/4];
		i += 1;
		if (i >= Nbytes) break; 
	}
}

void read_ECONT_no_address(uint32_t *iic, uint32_t ECONT_address, uint32_t *data, uint32_t Nbytes)
{
	int i;
	write_address(iic, (0b010 << 4) | (ECONT_address & 0xF), 1);
	wait_for_busy(iic);
	push_TX_FIFO(iic, Nbytes & 0xFF, 0, 1);
	wait_for_not_busy(iic);

	i = 0;
	while ((iic[0x104/4] & 0x40) != 0x40)
	{
		data[i] = iic[0x10C/4];
		i += 1;
		if (i >= Nbytes) break;
	}
}

void main(int argc, char **argv)
{
	int fd = open("/dev/mem", O_RDWR | O_SYNC);
	if (fd == -1)
	{
		printf("Cannot open /dev/mem\n");
		exit(1);
	}

	int i;
	uint32_t * iic;
	uint32_t data[16];

	for(i = 0; i < 16; ++i)
		data[i] = 0;

	iic = mmap(0, 0x1000UL, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x80020000);
	if (iic == (uint32_t*) -1)
	{
		printf("Cannot mmap IIC\n");
	}

	setup_iic(iic);

	// Write to the test register (address 0x0000)
	/*data[0] = time(NULL) & 0xFF;
	printf("Will write: 0x%02x\n", data[0]);
	write_ECONT(iic, 0b0000, 0x00000000, data, 1);*/

	//printf("SR: 0x%08x\n", iic[0x104/4]);
	//usleep(100000);
	//printf("SR: 0x%08x\n", iic[0x104/4]);
	
	// Read from the test register

	// TX sync word
	data[0] = 0x22;
	data[1] = 0x11;
	write_ECONT(iic, 0b0000, 0x03a9, data, 2);
	usleep(1000);

	data[0] = 0;
	data[1] = 0;
	read_ECONT(iic, 0b0000, 0x03a9, data, 2);
	printf("TX Sync word: 0x%02x%02x\n", data[1], data[0]);

	// Number of output ports enabled (bits 7:4)
	data[0] = 0xd0;
	write_ECONT(iic, 0b0000, 0x03a9 + 0x7, data, 1);
	usleep(1000);

	data[0] = 0;
	read_ECONT(iic, 0b0000, 0x03a9 + 0x7, data, 1);
	printf("Read back 0x%02x\n", data[0]);

	// Algorithm select
	data[0] = 0;
	write_ECONT(iic, 0b0000, 0x0454, data, 1);
	usleep(1000);

	data[0] = 0x999;
	read_ECONT(iic, 0b0000, 0x0454, data, 1);
	printf("Algorithm_sel_Density 0x%02x\n", data[0]);

	// Misc (bit 0 = clear errors?; bit 1 = run; others = unused)
	data[0] = 0x02;
	write_ECONT(iic, 0b0000, 0x0be9, data, 1);
	usleep(1000);

	data[0] = 0x00;
	read_ECONT(iic, 0b0000, 0x0be9, data, 1);
	printf("Misc RW 0x%02x\n", data[0]);

	// Set up channel aligner 0
	data[0] = 0x00;
	write_ECONT(iic, 0b0000, 0x0000, data, 1);
	usleep(1000);

	data[0] = 0xff;
	read_ECONT(iic, 0b0000, 0x0000, data, 1);
	printf("CHAL 00 RW config: 0x%02x\n", data[0]);

	data[0] = 0xff;
	read_ECONT(iic, 0b0000, 0x0001, data, 1);
	printf("CHAL 00 RW sel_override_val: 0x%02x\n", data[0]);

	// Take a snapshot of one channel's data
	data[0] = 0x00;
	write_ECONT(iic, 0b0000, 0x0380, data, 1);
	usleep(2000);

	data[0] = 0x02;
	write_ECONT(iic, 0b0000, 0x0380, data, 1);
	usleep(2000);

	data[0] = 0;
	read_ECONT(iic, 0b0000, 0x0380, data, 1);
	printf("Aligner config 0x%02x\n", data[0]);

	// Check that the snapshot is ready
	data[0] = 0xff;
	read_ECONT(iic, 0b0000, 0x0014, data, 1);
	printf("CHAL 00 RO status: 0x%02x\n", data[0]);

	// Read the snapshot
	for(i = 0; i < 16; i++)
		data[i] = 0xff;
	read_ECONT(iic, 0b0000, 0x0014 + 0x2, data, 14);
	for(i = 0; i < 14; i++)
		printf("Snapshot %2d: 0x%02x\n", i, data[i]);
	read_ECONT_no_address(iic, 0b0000, data, 10);
	for(i = 0; i < 10; i++)
		printf("Snapshot %2d: 0x%02x\n", i+14, data[i]);

	usleep(1000);

	data[0] = 0;
	read_ECONT(iic, 0b0000, 0x0380, data, 1);
	printf("Aligner config 0x%02x\n", data[0]);

	// Check that the snapshot is ready
	usleep(1000);
	data[0] = 0xff;
	read_ECONT(iic, 0b0000, 0x0014, data, 1);
	printf("CHAL 00 RO status: 0x%02x\n", data[0]);

	// Test repeated reads
	read_ECONT(iic, 0b0000, 0x0000, data, 1);
	printf("\n0x%02x\n", data[0]);
	read_ECONT_no_address(iic, 0b0000, data, 1);
	printf("0x%02x\n", data[0]);
	read_ECONT_no_address(iic, 0b0000, data, 2);
	printf("0x%02x\n", data[0]);
	printf("0x%02x\n", data[1]);
	read_ECONT_no_address(iic, 0b0000, data, 2);
	printf("0x%02x\n", data[0]);
	printf("0x%02x\n", data[1]);
	read_ECONT_no_address(iic, 0b0000, data, 2);
	printf("0x%02x\n", data[0]);
	printf("0x%02x\n", data[1]);

	read_ECONT(iic, 0b0000, 0x0000, data, 8);
	printf("\n0x%02x\n", data[0]);
	printf("0x%02x\n", data[1]);
	printf("0x%02x\n", data[2]);
	printf("0x%02x\n", data[3]);
	printf("0x%02x\n", data[4]);
	printf("0x%02x\n", data[5]);
	printf("0x%02x\n", data[6]);
	printf("0x%02x\n", data[7]);
}
