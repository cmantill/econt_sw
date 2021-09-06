#include <FastControlManager.h>

#include <iostream>
#include <sstream>
#include <cstring>

FastControlManager::FastControlManager(uhal::HwInterface* uhalHW)
{
  m_uhalHW = uhalHW;
}

// custom
void FastControlManager::resetFC()
{
  enable_FC_stream(0x1);
  force_idles(0x0);
  enable_orbit_sync(0x1);
  prel1a_offset(0x1); // any reason for this be 0?
  enable_global_l1a(0x0);
  enable_external_l1a(0x0);
  enable_random_l1a(0x0);
  enable_block_sequencer(0x0);

  // set_fc_channel_A_settings(enable, bx, prescale, flavor, length, follow)
  set_fc_channel_A_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
  set_fc_channel_B_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
  set_fc_channel_C_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
  set_fc_channel_D_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
  set_fc_channel_E_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
  set_fc_channel_F_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
  set_fc_channel_G_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);
  set_fc_channel_H_settings(0x0, 0x0, 0x0, FC_channel_flavor::L1A, 0x1, FC_channel_follow::DISABLE);

}
void FastControlManager::clear_link_reset_econt()
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_fast_ctrl_stream").write(0x1);
  m_uhalHW->getNode("fastcontrol_axi.command.enable_orbit_sync").write(0x1);
  m_uhalHW->getNode("fastcontrol_axi.request.link_reset_econt").write(0x0);
}

// commands
void FastControlManager::enable_FC_stream(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_fast_ctrl_stream").write(val);
}
void FastControlManager::force_idles(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.force_idles").write(val);
}
void FastControlManager::enable_orbit_sync(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_orbit_sync").write(val);
}
void FastControlManager::prel1a_offset(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.prel1a_offset").write(val);
}
void FastControlManager::enable_global_l1a(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.global_l1a_enable").write(val);
}
void FastControlManager::enable_external_l1a(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_external_l1as").write(val);
}
void FastControlManager::enable_random_l1a(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_random_l1a").write(val);
}
void FastControlManager::enable_block_sequencer(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_block_sequencer").write(val);
}
void FastControlManager::enable_nzs_generator(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_nsz_generator").write(val);
}
void FastControlManager::enable_nzs_jitter(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command.enable_nsz_jitter").write(val);
}

// requests
void FastControlManager::request_reset_nzs()
{
  m_uhalHW->getNode("fastcontrol_axi.request.reset_nzs").write(0x1);
}
void FastControlManager::request_count_rst()
{
  m_uhalHW->getNode("fastcontrol_axi.request.count_rst").write(0x1);
}
void FastControlManager::request_sequence()
{
  m_uhalHW->getNode("fastcontrol_axi.request.sequence_req").write(0x1);
}
void FastControlManager::request_orbit_rst()
{
  m_uhalHW->getNode("fastcontrol_axi.request.orbit_rst").write(0x1);
}
void FastControlManager::request_chipsynq()
{
  m_uhalHW->getNode("fastcontrol_axi.request.chipsynq").write(0x1);
}
void FastControlManager::request_ebr()
{
  m_uhalHW->getNode("fastcontrol_axi.request.ebr").write(0x1);
}
void FastControlManager::request_ecr()
{
  m_uhalHW->getNode("fastcontrol_axi.request.ecr").write(0x1);
}
void FastControlManager::request_link_reset_roct()
{
  m_uhalHW->getNode("fastcontrol_axi.request.link_reset_roct").write(0x1);
}
void FastControlManager::request_link_reset_rocd()
{
  m_uhalHW->getNode("fastcontrol_axi.request.link_reset_rocd").write(0x1);
}
void FastControlManager::request_link_reset_econt()
{
  m_uhalHW->getNode("fastcontrol_axi.request.link_reset_econt").write(0x1);
}
void FastControlManager::request_link_reset_econd()
{
  m_uhalHW->getNode("fastcontrol_axi.request.link_reset_econd").write(0x1);
}

// BX for requests
void FastControlManager::bx_orbit_synq(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_orbit_synq").write(val);
}
void FastControlManager::bx_chipsynq(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_chipsynq").write(val);
}
void FastControlManager::bx_ebr(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_ebr").write(val);
}
void FastControlManager::bx_ecr(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_ecr").write(val);
}
void FastControlManager::bx_link_reset_roct(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_link_reset_roct").write(val);
}
void FastControlManager::bx_link_reset_rocd(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_link_reset_rocd").write(val);
}
void FastControlManager::bx_link_reset_econt(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_link_reset_econt").write(val);
}
void FastControlManager::bx_link_reset_econd(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.bx_link_reset_econd").write(val);
}

// l1a settings
void FastControlManager::minimum_trigger_period(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.minimum_trigger_period").write(val);
}
void FastControlManager::random_trigger_log2_period(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.random_trigger_log2_period").write(val);
}
void FastControlManager::external_triggers_debounce(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.external_triggers_debounce").write(val);
}
void FastControlManager::external_trigger_delay(int chan, int val)
{
  char buf[200];
  sprintf(buf,"%s%d","fastcontrol_axi.external_trigger_delay.bit",chan);
  m_uhalHW->getNode(buf).write(val);
}
void FastControlManager::external_trigger_delay(int val)
{
  for(int i=0; i<4; i++)
    this->external_trigger_delay(i,val);
}

// sequencer settings
void FastControlManager::command_sequence_length(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command_sequence.length").write(val);
}
void FastControlManager::command_sequence_bx(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command_sequence.bx").write(val);
}
void FastControlManager::command_sequence_orbit_prescale(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command_sequence.orbit_prescale").write(val);
}
void FastControlManager::command_sequence_page(int val)
{
  m_uhalHW->getNode("fastcontrol_axi.command_sequence.page").write(val);
}
void FastControlManager::command_sequence_contents(const std::vector<uint32_t>& vec)
{
  m_uhalHW->getNode("fastcontrol_axi.command_sequence.contents").writeBlock(vec);
}

// periodic generator settings
void FastControlManager::set_fc_periodic_settings(int periodic_chan, int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow)
{
  char enablebuf[200], flavorbuf[200], enablefollowbuf[200], followwhichbuf[200], bxbuf[200], prescalebuf[200], lengthbuf[200];
  sprintf(enablebuf      ,"%s%d%s","fastcontrol_axi.periodic",periodic_chan,".enable");
  sprintf(flavorbuf      ,"%s%d%s","fastcontrol_axi.periodic",periodic_chan,".flavor");
  sprintf(enablefollowbuf,"%s%d%s","fastcontrol_axi.periodic",periodic_chan,".enable_follow");
  sprintf(followwhichbuf ,"%s%d%s","fastcontrol_axi.periodic",periodic_chan,".follow_which");
  sprintf(bxbuf          ,"%s%d%s","fastcontrol_axi.periodic",periodic_chan,".bx");
  sprintf(prescalebuf    ,"%s%d%s","fastcontrol_axi.periodic",periodic_chan,".orbit_prescale");
  sprintf(lengthbuf      ,"%s%d%s","fastcontrol_axi.periodic",periodic_chan,".burst_length");

  switch(flavor){
  case FC_channel_flavor::L1A       : m_uhalHW->getNode(flavorbuf).write(0x0); break;
  case FC_channel_flavor::L1A_NZS   : m_uhalHW->getNode(flavorbuf).write(0x1); break;
  case FC_channel_flavor::CALPULINT : m_uhalHW->getNode(flavorbuf).write(0x2); break;
  case FC_channel_flavor::CALPULEXT : m_uhalHW->getNode(flavorbuf).write(0x3); break;
  case FC_channel_flavor::EXTPULSE0 : m_uhalHW->getNode(flavorbuf).write(0x4); break;
  case FC_channel_flavor::EXTPULSE1 : m_uhalHW->getNode(flavorbuf).write(0x5); break;
  }
  switch(follow){
  case FC_channel_follow::DISABLE  : m_uhalHW->getNode(enablefollowbuf).write(0x0); break;
  case FC_channel_follow::A:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x0); break;
  case FC_channel_follow::B:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x1); break;
  case FC_channel_follow::C:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x2); break;
  case FC_channel_follow::D:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x3); break;
  case FC_channel_follow::E:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x4); break;
  case FC_channel_follow::F:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x5); break;
  case FC_channel_follow::G:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x6); break;
  case FC_channel_follow::H:         m_uhalHW->getNode(enablefollowbuf).write(0x1); m_uhalHW->getNode(followwhichbuf).write(0x7); break;
  }
  m_uhalHW->getNode(enablebuf).write(enable);
  m_uhalHW->getNode(bxbuf).write(bx);
  m_uhalHW->getNode(prescalebuf).write(prescale);
  m_uhalHW->getNode(lengthbuf).write(length);
}

void FastControlManager::set_fc_channel_A_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow)
{
  this->set_fc_periodic_settings(0, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_B_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
  this->set_fc_periodic_settings(1, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_C_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
  this->set_fc_periodic_settings(2, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_D_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
  this->set_fc_periodic_settings(3, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_E_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
  this->set_fc_periodic_settings(4, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_F_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
  this->set_fc_periodic_settings(5, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_G_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow) 
{
  this->set_fc_periodic_settings(6, enable, bx, prescale, flavor, length, follow);
}
void FastControlManager::set_fc_channel_H_settings(int enable, int bx, int prescale, FC_channel_flavor flavor, int length, FC_channel_follow follow)
{
  this->set_fc_periodic_settings(7, enable, bx, prescale, flavor, length, follow);
} 

void FastControlManager::setRegister( std::string reg, int val )
{
  char buf[200];
  sprintf(buf,"%s.%s","fastcontrol_axi",reg.c_str());
  m_uhalHW->getNode(buf).write(val);
}

void FastControlManager::setRecvRegister( std::string reg, int val )
{
  char buf[200];
  sprintf(buf,"%s.%s","fastcontrol_recv_axi",reg.c_str());
  m_uhalHW->getNode(buf).write(val);
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
