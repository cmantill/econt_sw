#include <FastControlManager.h>

#include <iostream>
#include <sstream>
#include <cstring>

FastControlManager::FastControlManager(uhal::HwInterface* uhalHW)
{
  m_uhalHW = uhalHW;
}
void FastControlManager::resetFC()
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_fast_ctrl_stream").write(0x1);
  m_uhalHW->getNode("fastcontrol_axi.command.force_idles").write(0x0);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_orbit_sync").write(0x1);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_per_calib_req").write(0x0);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_calib_l1a").write(0x0);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_periodic_l1a_A").write(0x0);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_periodic_l1a_B").write(0x0);
}
void FastControlManager::clear_link_reset()
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_fast_ctrl_stream").write(0x1);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_orbit_sync").write(0x1);
  m_uhalHW->getNode("fastcontrol_axi.command.link_reset").write(0x0);
}

void FastControlManager::enable_FC_stream(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_fast_ctrl_stream").write(val);
}
void FastControlManager::enable_orbit_sync(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_orbit_sync").write(val);
}
void FastControlManager::enable_periodic_calib_req(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_per_calib_req").write(val);
}
void FastControlManager::enable_calib_l1a(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_calib_l1a").write(val);
}
void FastControlManager::enable_periodic_l1a_A(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_periodic_l1a_A").write(val);
}

void FastControlManager::enable_periodic_l1a_B(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_periodic_l1a_B").write(val);
}

void FastControlManager::enable_external_l1a(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_external_l1a_1").write((val & 0x1)?1:0);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_external_l1a_2").write((val & 0x2)?1:0);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_external_l1a_3").write((val & 0x4)?1:0);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_external_l1a_4").write((val & 0x8)?1:0);
}

void FastControlManager::gen_calib_cycle(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.gen_calib_cycle").write(val);
}

void FastControlManager::orbit_rst(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.orbit_rst").write(val);
}

void FastControlManager::link_reset(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.link_reset").write(val);
}

void FastControlManager::daq_resync(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.daq_resync").write(val);
}

void FastControlManager::l1a_A(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.l1a_A").write(val);
}

void FastControlManager::l1a_B(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.l1a_B").write(val);
}

void FastControlManager::test_req(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.test_req").write(val);
}

void FastControlManager::count_rst(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.count_rst").write(val);
}

void FastControlManager::set_calib_req_bx(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_calib.req").write(val);
}

void FastControlManager::set_calib_l1a_bx(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_calib.l1a").write(val);
}

void FastControlManager::set_calib_l1a_notcalib(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_calib.l1a_notcalib").write(val);
}

void FastControlManager::set_l1a_A_bx(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_A.l1a").write(val);
}

void FastControlManager::set_l1a_A_prescale(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_A.orbit_prescale").write(val);
}

void FastControlManager::set_l1a_B_bx(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_B.l1a").write(val);
}

void FastControlManager::set_l1a_B_prescale(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_B.orbit_prescale").write(val);
}

void FastControlManager::set_l1a_rand_period(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.log_l1a_rand_bx_period").write(val);
}

void FastControlManager::set_l1a_min_bx(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.l1a_settings.bx_spacing").write(val);
}

void FastControlManager::set_l1a_burst_len(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.l1a_settings.l1a_burst_len").write(val);
}

void FastControlManager::set_l1a_ext_debounce(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.l1a_settings.external_debounce").write(val);
}

void FastControlManager::set_link_reset_bx(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_link_reset").write(val);
}

void FastControlManager::enable_random_l1a(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_random_l1a").write(val);
}


const uint32_t FastControlManager::getRegister( std::string reg )
{
  char buf[200];
  sprintf(buf,"%s.%s","fastcontrol_axi",reg.c_str());
  uhal::ValWord<uint32_t> val=m_uhalHW->getNode(buf).read();
  m_uhalHW->dispatch();
  return (uint32_t)val;
}

const uint32_t FastControlManager::getRecvRegister( std::string reg )
{
  char buf[200];
  sprintf(buf,"%s.%s","fastcontrol_recv_axi",reg.c_str());
  uhal::ValWord<uint32_t> val=m_uhalHW->getNode(buf).read();
  m_uhalHW->dispatch();
  return (uint32_t)val;
}
