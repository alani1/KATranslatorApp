
class GenerateSSML(object):
    """Merge Subtitles and generate SSML"""

    def __init__(self,filename):
        """Constructor"""
        self.readSubtitles(filename)

    def readSubtitles(self,filename):
        """Read Subtitle File"""
        #Open file and read srt-format subtitles into array

        # Open the .srt file
        with open(filename, 'r') as f:
            srt_data = f.read()

        # Split the .srt data into subtitle blocks
        subtitle_blocks = srt_data.split('\n\n')
    
        # Merge the subtitles
        merged_subtitles = self.merge_subtitles(subtitle_blocks)

        for subtitle in merged_subtitles:
            print("\nSUBTITLE:\n" + subtitle)
        #print(merged_subtitles)
        # Write the merged subtitles to a new .srt file
        #with open('merged_subtitles.srt', 'w') as f:
        #    for i in range(len(merged_subtitles)):
        #        f.write(str(i+1) + '\n' + merged_subtitles[i] + '\n\n')        


    # Define a function to convert a time string to seconds
    def time_to_seconds(self, time_str):
        hours, minutes, seconds = map(float, time_str.replace(',', '.').split(':'))
        return hours * 3600 + minutes * 60 + seconds                

    # Define a function to merge subtitles based on pauses
    def merge_subtitles(self, subtitle_blocks, pause_time=0.5):
        merged_subtitles = []
        current_subtitle = ''
        current_end_time = 0
        for subtitle in subtitle_blocks:
            # Split the subtitle into lines and extract the start and end times
            lines = subtitle.split('\n')
            start_time, end_time = lines[1].split(' --> ')
            start_time = self.time_to_seconds(start_time)
            end_time = self.time_to_seconds(end_time)

            print(lines[2])
            print("duration: " + str(end_time - start_time))
            print("pause: " + str(start_time - current_end_time))
            print("\n")
            # Check if there is a pause between this subtitle and the current one
            if start_time - current_end_time > pause_time:
                merged_subtitles.append(current_subtitle.strip())
                current_subtitle = lines[2] + '\n'
            else:
                current_subtitle += lines[2] + '\n'
            current_end_time = end_time
        # Add the last subtitle to the merged subtitles
        merged_subtitles.append(current_subtitle.strip())
        return merged_subtitles                


    # Define a function to split subtitles into sentences
    def split_into_sentences(self, subtitle_text):
        # Split the subtitle into sentences using regex
        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s'
        sentences = re.split(sentence_pattern, subtitle_text)
        return sentences

    # Define a function to merge subtitles based on sentences and pauses
    def mergeSplit_subtitles(self, subtitle_blocks):
        merged_subtitles = []
        for i in range(len(subtitle_blocks)):
            subtitle_text = subtitle_blocks[i]
            # Split the subtitle into sentences
            # sentences = split_into_sentences(subtitle_text)
            # Check if there is a pause between the last sentence of this subtitle and the first sentence of the next subtitle
            if i < len(subtitle_blocks) - 1:
                next_subtitle_text = subtitle_blocks[i+1]
                next_sentences = split_into_sentences(next_subtitle_text)
                pause_between_subtitles = False
                if len(sentences) > 0 and len(next_sentences) > 0:
                    last_sentence = sentences[-1]
                    first_sentence = next_sentences[0]
                    if len(last_sentence) > 0 and len(first_sentence) > 0:
                        last_word = last_sentence.split()[-1]
                        first_word = first_sentence.split()[0]
                        if last_word.endswith('.') and first_word.islower():
                            pause_between_subtitles = True
                # Merge the subtitle with the next subtitle if there is a pause between them
                if pause_between_subtitles:
                    merged_subtitles.append(subtitle_text + '\n' + next_subtitle_text)
                else:
                    merged_subtitles.append(subtitle_text)
            else:
                merged_subtitles.append(subtitle_text)
        return merged_subtitles
     
      
if __name__ == '__main__':
    print("Hello World")

    #st = Subtitles("Psl3LWRAysQ")
    
    
    ssml = GenerateSSML(".\data\Psl3LWRAysQ.srt")
