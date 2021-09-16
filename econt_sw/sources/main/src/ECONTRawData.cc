#include <ECONTRawData.h>

#include <algorithm>
#include <iomanip>

ECONTRawData::ECONTRawData(int event, 
			   std::vector<uint32_t>::const_iterator data_begin,
			   std::vector<uint32_t>::const_iterator data_end
			   ) : m_data(data_begin, data_end)
{
  m_event=event;
}

ECONTRawData::ECONTRawData(int event,
			   const std::vector<uint32_t> &data)
{
  m_event=event;
  std::copy( data.begin(), data.end(), std::back_inserter(m_data) );
}

std::ostream& operator<<(std::ostream& out,const ECONTRawData& rawdata)
{
  out << "event = " << std::dec << rawdata.m_event  << std::endl;
  for( auto d : rawdata.m_data )
    out << "\t" << std::hex << std::setfill('0') << std::setw(8) << d ;
  out << std::endl;
  return out;
}

ECONTEventContainer::ECONTEventContainer()
{
  m_rawdata=std::vector<uint32_t>(ECONT_DATA_BUF_SIZE,0);
}

void ECONTEventContainer::fillContainer( int eventID, const std::vector<uint32_t>& data)
{
  m_mutex.lock();
  unsigned int len = data.size()/ECONT_DATA_BUF_SIZE;
  for( unsigned int iEvt = 0; iEvt < len; ++iEvt ){
    auto header = data.begin() + iEvt * ECONT_DATA_BUF_SIZE;
    m_econtdata.emplace_back( new ECONTRawData(eventID, header, header+ECONT_DATA_BUF_SIZE) );
    eventID++;
  }
  m_mutex.unlock();
}
