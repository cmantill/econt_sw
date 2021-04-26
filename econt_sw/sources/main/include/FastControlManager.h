#ifndef FASTCONTROLMANAGER
#define FASTCONTROLMANAGER 1

#include <uhal/uhal.hpp>

class FastControlManager
{
 public:
  FastControlManager(uhal::HwInterface* uhalHW);
  ~FastControlManager(){;}
  void resetFC();
  void link_reset_l1a();
  void clear_link_reset_l1a();
  void send_link_reset_l1a();

  void enable_FC_stream(int val);
  void enable_orbit_sync(int val);
  void enable_per_calib_req(int val);
  void enable_periodic_calib_req(int val);
  void enable_calib_l1a(int val);
  void enable_periodic_l1a_A(int val);
  void enable_periodic_l1a_B(int val);
  void enable_external_l1a(int val);
  void enable_random_l1a(int val);
  void gen_calib_cycle(int val);
  void orbit_rst(int val);
  void link_reset(int val);
  void daq_resync(int val);
  void l1a_A(int val);
  void l1a_B(int val);
  void test_req(int val);
  void count_rst(int val);

  void set_calib_req_bx(int val);
  void set_calib_l1a_bx(int val);
  void set_calib_l1a_notcalib(int val);
  void set_l1a_A_bx(int val);
  void set_l1a_A_prescale(int val);
  void set_l1a_B_bx(int val);
  void set_l1a_B_prescale(int val);
  void set_l1a_rand_period(int val);
  void set_l1a_min_bx(int val);
  void set_l1a_burst_len(int val);
  void set_l1a_ext_debounce(int val);
  void set_link_reset_bx(int val);

  const uint32_t getRegister( std::string reg );
  const uint32_t getRecvRegister( std::string reg );
  
 private:
  uhal::HwInterface* m_uhalHW;
};

#endif
